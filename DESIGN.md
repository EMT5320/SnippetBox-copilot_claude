# 设计与权衡说明

## 数据模型

采用单表设计,包含核心字段:id、title、content、tags(JSON)、时间戳、软删标记和content_hash(用于幂等)。选择SQLite便于开发和部署,支持切换PostgreSQL。tags存储为JSON字符串,便于灵活扩展而无需额外表。

## 索引策略

创建三类索引:
1. `deleted_at`索引:过滤软删记录,提升查询性能
2. `content_hash`唯一索引:保证幂等性并快速检查重复
3. `created_at`降序索引:支持按创建时间排序分页
4. FTS5全文索引:对title和content进行高效全文检索

FTS5虚拟表通过触发器自动同步,空间换时间。

## 速率限制实现

采用内存滑动窗口:middleware维护每IP的请求时间戳列表,每次请求清理1分钟外的记录并计数。仅对写操作(POST/PATCH/DELETE)限流。优点:实现简单、无外部依赖;缺点:多实例需共享存储(可用Redis)。

## 幂等策略

创建时计算`SHA256(title||content)`作为唯一标识。先查询是否存在该hash,存在则返回已有记录,否则插入。trade-off:牺牲少量计算换取业务幂等性,避免重复提交。

## 日志与可观测性

使用结构化JSON日志,每条记录包含timestamp、level、message、trace_id及业务字段。trace_id通过contextvars在请求生命周期传递,便于分布式追踪。中间件自动记录请求开始/结束及耗时。/health端点返回状态和时间戳供监控探活。

## 安全基线

Pydantic自动校验输入类型、长度、必填项;参数化查询(aiosqlite)防SQL注入;CORS可配置origin列表;所有错误统一格式,避免信息泄露。
