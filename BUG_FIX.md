# 已知缺陷注入说明

## 缺陷内容

**并发创建相同片段的竞态条件(Race Condition)**

在`src/crud.py`的`create_snippet`函数中,幂等性检查采用"先查询后插入"的非原子操作:
```python
# 1. 查询是否存在
existing = await conn.execute("SELECT ... WHERE content_hash = ?")
if existing:
    return existing

# 2. 不存在则插入
await conn.execute("INSERT INTO snippets ...")
```

当多个并发请求同时创建相同片段时,可能都通过检查(步骤1)后同时插入(步骤2),导致:
- 违反`content_hash`唯一约束,抛出异常
- 或在某些情况下创建多条重复记录

## 复现步骤

1. 运行测试: `pytest tests/test_concurrency.py -v`
2. 该测试同时发送10个创建相同片段的请求
3. 观察输出: 可能看到多个不同ID或数据库错误

## 修复方案

### 核心修复点

使用数据库级别的原子操作:`INSERT OR IGNORE` + 查询已存在记录

**修复后的代码** (`src/crud.py`):

```python
async def create_snippet(db: AsyncSession, snippet_data: SnippetCreate) -> Snippet:
    """Create a new snippet with idempotency check (race-condition safe)."""
    content_hash = compute_content_hash(snippet_data.title, snippet_data.content)
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        
        # 原子性操作: 尝试插入,如果hash冲突则忽略
        try:
            tags_json = serialize_tags(snippet_data.tags)
            cursor = await conn.execute(
                """INSERT OR IGNORE INTO snippets (title, content, tags, content_hash) 
                   VALUES (?, ?, ?, ?)""",
                (snippet_data.title, snippet_data.content, tags_json, content_hash)
            )
            await conn.commit()
        except Exception as e:
            # 如果有其他数据库错误,回滚
            await conn.rollback()
            raise
        
        # 无论插入成功与否,查询返回已存在的记录
        cursor = await conn.execute(
            "SELECT * FROM snippets WHERE content_hash = ? AND deleted_at IS NULL",
            (content_hash,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise CRUDException("CREATE_FAILED", "Failed to create or retrieve snippet")
        
        return Snippet(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            tags=row['tags'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            content_hash=row['content_hash']
        )
```

### 关键改进

1. **INSERT OR IGNORE**: SQLite原子操作,遇到唯一约束冲突时静默忽略
2. **统一查询**: 插入后总是查询确保返回正确记录(无论是新建还是已存在)
3. **事务安全**: 发生异常时回滚,保证数据一致性

### 验证修复

应用修复后运行:
```bash
pytest tests/test_concurrency.py -v
```

预期结果: 所有并发请求返回相同ID,无异常抛出。

## 根本原因分析

原实现的check-then-act模式在并发环境下不安全。数据库的UNIQUE约束虽然能防止重复,但会导致部分请求失败。正确做法是利用数据库的原子性保证,结合OR IGNORE处理冲突,确保幂等语义。
