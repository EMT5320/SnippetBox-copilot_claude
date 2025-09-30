# 可维护性与可读性约定

## 目录规范

```
项目采用标准Python应用结构:
- src/: 源代码,按职责分模块(config/database/models/schemas/crud/middleware/utils)
- tests/: 测试代码,按功能分文件(api/idempotency/rate_limit/concurrency)
- scripts/: 工具脚本(init_db/load_test)
- migrations/: 数据库迁移SQL
- 配置文件置于根目录(.env/requirements.txt/pytest.ini/Dockerfile等)
```

## 命名规范

- **文件**: 小写下划线 `snake_case.py`
- **类**: 大驼峰 `PascalCase`
- **函数/变量**: 小写下划线 `snake_case`
- **常量**: 大写下划线 `UPPER_SNAKE_CASE`
- **私有**: 下划线前缀 `_private_method`

## 代码组织

- 每个文件顶部docstring说明用途
- 函数/类包含类型提示和文档字符串
- 相关功能分组(CRUD操作集中在crud.py,数据模型在models.py)
- 依赖注入优先(使用FastAPI的Depends)
- 避免循环依赖(utils不导入业务模块)

## 异步规范

- 所有I/O操作使用async/await
- 数据库操作使用aiosqlite
- HTTP请求使用httpx AsyncClient
- 测试使用pytest-asyncio

## 错误处理

- 业务错误抛出自定义异常(CRUDException)
- 统一异常处理器格式化错误响应
- 所有错误包含error_code/message/trace_id
- 日志记录错误详情

## 测试规范

- 测试类以Test开头,测试函数以test_开头
- 使用fixture共享测试设置
- 测试文件与功能模块对应
- 集成测试使用独立测试数据库

## Lint与Format

推荐工具:
- **Formatter**: `black` (代码格式化)
- **Linter**: `flake8` (代码检查)
- **Type Checker**: `mypy` (类型检查)
- **Import Sort**: `isort` (导入排序)

配置示例:
```bash
pip install black flake8 mypy isort
black src/ tests/
flake8 src/ tests/ --max-line-length=120
isort src/ tests/
```

## 文档规范

- README.md: 快速开始和基本使用
- API_SPEC.md: 完整API规格
- DESIGN.md: 架构设计决策
- BUG_FIX.md: 已知问题与修复
- 代码内注释说明复杂逻辑

## Git规范

推荐commit格式:
```
<type>: <subject>

<body>

Types: feat/fix/docs/style/refactor/test/chore
```

示例:
```
feat: add rate limiting middleware
fix: resolve race condition in idempotent creation
docs: update API specification
test: add concurrency test cases
```

## 性能考虑

- 数据库查询使用索引
- 分页限制最大page_size
- 日志异步写入(使用handlers)
- 避免N+1查询
- 静态资源使用CDN(如适用)

## 安全检查清单

- [ ] 输入验证(Pydantic)
- [ ] SQL注入防护(参数化查询)
- [ ] XSS防护(API不直接渲染HTML)
- [ ] CORS配置
- [ ] 速率限制
- [ ] 敏感信息不记录日志
- [ ] 依赖定期更新

## 部署检查清单

- [ ] 环境变量配置
- [ ] 数据库迁移执行
- [ ] 日志级别设置为INFO/WARNING
- [ ] 健康检查端点可访问
- [ ] CORS origins配置正确
- [ ] 速率限制启用
- [ ] 备份策略(数据库)
