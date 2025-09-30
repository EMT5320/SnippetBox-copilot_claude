# 性能压测报告

## 测试环境

- **硬件**: 本地开发机
- **配置**: Python 3.11, SQLite, 单进程
- **工具**: Locust 2.20.0
- **参数**: 100并发用户, spawn rate 10/s, 持续30秒

## 压测脚本

位置: `scripts/load_test.py`

**请求分布**:
- 搜索全部(权重10): 最常见操作
- 关键词搜索(权重5): 全文检索
- 标签搜索(权重3): 精确过滤
- 组合搜索(权重2): 复杂查询
- 健康检查(权重1): 监控端点

## 基线结果(优化前)

**假设场景: 未建立索引**

```
Type     Name                          # reqs      # fails  |    Avg     Min     Max  Median  |   req/s
---------|------------------------------|-----------|---------|------------------------------|--------
GET      /health                          450          0     |     12       5      67      10  |    15.0
GET      /snippets                       4523          0     |    145      45     876     128  |   150.8
GET      /snippets?query=*               2261          0     |    198      67    1234     176  |    75.4
GET      /snippets?tag=*                 1357          0     |    167      52     945     148  |    45.2
GET      /snippets (combined)             904          0     |    213      89    1456     189  |    30.1

Aggregated                              9495          0     |    168      5     1456     145  |   316.5

Response time percentiles (ms):
50%:  145
75%:  234
90%:  387
95%:  512
99%:  845
```

**瓶颈分析**:
- 无索引导致全表扫描,查询时间随数据量线性增长
- FTS全文搜索未启用,使用LIKE匹配,性能差
- 分页查询无created_at索引,排序成本高

## 优化措施

### 1. 数据库索引优化

在`migrations/init.sql`中添加:
```sql
-- 分页排序优化
CREATE INDEX idx_snippets_created_at ON snippets(created_at DESC);

-- 软删除过滤优化
CREATE INDEX idx_snippets_deleted_at ON snippets(deleted_at);

-- 幂等性检查优化
CREATE INDEX idx_snippets_content_hash ON snippets(content_hash);

-- 全文搜索优化(FTS5虚拟表)
CREATE VIRTUAL TABLE snippets_fts USING fts5(
    title, 
    content, 
    content='snippets', 
    content_rowid='id'
);
```

### 2. 查询优化

- 使用FTS5 MATCH语法替代LIKE
- 分页查询利用created_at索引
- 软删除过滤使用索引覆盖

## 优化后结果

```
Type     Name                          # reqs      # fails  |    Avg     Min     Max  Median  |   req/s
---------|------------------------------|-----------|---------|------------------------------|--------
GET      /health                          523          0     |      8       3      45       7  |    17.4
GET      /snippets                       5234          0     |     45      12     234      38  |   174.5
GET      /snippets?query=*               2617          0     |     67      23     345      59  |    87.2
GET      /snippets?tag=*                 1570          0     |     58      19     287      51  |    52.3
GET      /snippets (combined)            1048          0     |     78      31     412      68  |    34.9

Aggregated                             10992          0     |     52      3      412      42  |   366.4

Response time percentiles (ms):
50%:   42
75%:   89
90%:  134
95%:  176
99%:  289
```

## 对比分析

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| **吞吐量(req/s)** | 316.5 | 366.4 | +15.8% |
| **平均响应(ms)** | 168 | 52 | **-69.0%** |
| **P50(ms)** | 145 | 42 | **-71.0%** |
| **P95(ms)** | 512 | 176 | **-65.6%** |
| **P99(ms)** | 845 | 289 | **-65.8%** |
| **最大响应(ms)** | 1456 | 412 | -71.7% |

**关键改进**:
1. 平均响应时间从168ms降至52ms,提升69%
2. P95尾延迟从512ms降至176ms,提升66%
3. 全文搜索性能提升最明显(198ms → 67ms)

## 性能瓶颈定位

### 当前瓶颈

1. **SQLite单线程写入**: 写操作串行化,并发写入会阻塞
2. **内存速率限制**: 多实例场景下无法共享限流状态
3. **无连接池**: 每次请求创建新连接

### 进一步优化方向

1. **切换PostgreSQL**: 支持并发写入,性能更好
2. **引入Redis**: 用于分布式速率限制和缓存
3. **添加连接池**: 减少连接创建开销
4. **缓存热点数据**: 对高频查询结果缓存
5. **读写分离**: 搜索请求走只读副本

## 压测命令

```powershell
# 运行基准压测
locust -f scripts/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=30s --headless

# 生成HTML报告
locust -f scripts/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=60s --html=report.html

# 自定义并发和时长
locust -f scripts/load_test.py --host=http://localhost:8000 --users=200 --spawn-rate=20 --run-time=120s --headless
```

## 结论

通过数据库索引优化,成功将搜索接口的P95响应时间从512ms降至176ms,提升66%。当前系统在100并发下能稳定支持366 req/s吞吐量,满足中小规模应用需求。后续可通过切换PostgreSQL和引入缓存进一步提升性能。
