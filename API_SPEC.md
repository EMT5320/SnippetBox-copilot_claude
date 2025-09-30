# SnippetBox API 规格文档

## 基础信息
- **Base URL**: `http://localhost:8000`
- **API Version**: 1.0.0
- **Content-Type**: `application/json`

## 错误码表

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| `SNIPPET_NOT_FOUND` | 404 | 片段不存在或已删除 |
| `RATE_LIMIT_EXCEEDED` | 429 | 超过速率限制 |
| `CREATE_FAILED` | 500 | 创建失败 |
| `UPDATE_FAILED` | 500 | 更新失败 |
| `DELETE_FAILED` | 500 | 删除失败 |
| `SEARCH_FAILED` | 500 | 搜索失败 |
| `INTERNAL_ERROR` | 500 | 内部错误 |
| `HTTP_ERROR` | 4xx/5xx | 其他HTTP错误 |

所有错误响应格式：
```json
{
  "error_code": "ERROR_CODE",
  "message": "Error description",
  "trace_id": "uuid"
}
```

## 端点详情

### 1. 健康检查

**GET /health**

检查服务健康状态。

**响应示例**:
```json
{
  "status": "ok",
  "time": "2025-09-30T10:30:00.000Z"
}
```

---

### 2. 创建代码片段

**POST /snippets**

创建新的代码片段。支持幂等性：相同title+content会返回已存在的片段。

**请求体**:
```json
{
  "title": "Python Hello World",
  "content": "print('Hello, World!')",
  "tags": ["python", "beginner", "tutorial"]
}
```

**字段说明**:
- `title` (必填): 标题,1-200字符
- `content` (必填): 代码内容,1-100000字符
- `tags` (可选): 标签数组,最多20个,每个最长50字符

**成功响应** (201 Created):
```json
{
  "id": 1,
  "created_at": "2025-09-30T10:30:00.123456"
}
```

**验证错误** (422):
```json
{
  "detail": [
    {
      "loc": ["body", "title"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

### 3. 获取单个片段

**GET /snippets/{id}**

根据ID获取代码片段详情。

**路径参数**:
- `id`: 片段ID (整数)

**成功响应** (200 OK):
```json
{
  "id": 1,
  "title": "Python Hello World",
  "content": "print('Hello, World!')",
  "tags": ["python", "beginner"],
  "created_at": "2025-09-30T10:30:00.123456",
  "updated_at": "2025-09-30T10:30:00.123456"
}
```

**未找到** (404):
```json
{
  "error_code": "SNIPPET_NOT_FOUND",
  "message": "Snippet with ID 999 not found",
  "trace_id": "abc-123"
}
```

---

### 4. 搜索片段

**GET /snippets**

搜索代码片段,支持全文检索、标签过滤和分页。

**查询参数**:
- `query` (可选): 全文搜索关键词,匹配title和content
- `tag` (可选): 标签过滤
- `page` (可选): 页码,默认1,最小1
- `page_size` (可选): 每页数量,默认20,范围1-100

**请求示例**:
```
GET /snippets?query=python&tag=tutorial&page=1&page_size=10
```

**成功响应** (200 OK):
```json
{
  "total": 42,
  "page": 1,
  "page_size": 10,
  "items": [
    {
      "id": 1,
      "title": "Python Tutorial",
      "content": "def hello(): ...",
      "tags": ["python", "tutorial"],
      "created_at": "2025-09-30T10:30:00.123456",
      "updated_at": "2025-09-30T10:30:00.123456"
    }
  ]
}
```

---

### 5. 更新片段

**PATCH /snippets/{id}**

部分更新代码片段。所有字段都是可选的。

**路径参数**:
- `id`: 片段ID

**请求体** (至少提供一个字段):
```json
{
  "title": "Updated Title",
  "content": "new code...",
  "tags": ["new", "tags"]
}
```

**成功响应** (200 OK):
```json
{
  "id": 1,
  "title": "Updated Title",
  "content": "new code...",
  "tags": ["new", "tags"],
  "created_at": "2025-09-30T10:30:00.123456",
  "updated_at": "2025-09-30T11:00:00.789012"
}
```

---

### 6. 删除片段

**DELETE /snippets/{id}**

软删除代码片段(标记删除,不物理删除)。

**路径参数**:
- `id`: 片段ID

**成功响应** (204 No Content):
无响应体

**未找到** (404):
```json
{
  "error_code": "SNIPPET_NOT_FOUND",
  "message": "Snippet with ID 999 not found",
  "trace_id": "abc-123"
}
```

---

## 速率限制

- **限制**: 每IP每分钟60次写操作 (POST/PATCH/DELETE)
- **读操作**: 不限制
- **超限响应** (429):
```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded. Maximum 60 write operations per minute.",
  "trace_id": "abc-123"
}
```

---

## 幂等性

创建片段时,如果已存在相同的`title`+`content`组合(基于SHA256哈希),将返回已存在片段的信息,而不是创建新片段。

示例:
```bash
# 第一次创建
POST /snippets {"title":"A", "content":"B"} → {id:1, ...}

# 第二次创建相同内容
POST /snippets {"title":"A", "content":"B"} → {id:1, ...} # 返回同一ID
```

---

## 全局响应头

所有响应都包含:
- `X-Trace-ID`: 请求跟踪ID,用于日志关联

---

## 完整示例流程

```bash
# 1. 检查服务健康
curl http://localhost:8000/health

# 2. 创建片段
curl -X POST http://localhost:8000/snippets \
  -H "Content-Type: application/json" \
  -d '{"title":"Quick Sort","content":"def quicksort(arr): ...","tags":["python","algorithm"]}'

# 3. 搜索片段
curl "http://localhost:8000/snippets?query=sort&page=1&page_size=10"

# 4. 获取片段详情
curl http://localhost:8000/snippets/1

# 5. 更新片段
curl -X PATCH http://localhost:8000/snippets/1 \
  -H "Content-Type: application/json" \
  -d '{"tags":["python","algorithm","sorting"]}'

# 6. 删除片段
curl -X DELETE http://localhost:8000/snippets/1
```
