## 智能体平台（FastAPI + LangChain）

该项目是一个基于 **FastAPI** + **LangChain** 的智能体平台脚手架，集成：

- 可配置数据库（MySQL / PostgreSQL）
- 可配置 LLM（通过 `app/config/config.yaml`）
- 使用 Milvus 存储对话向量记忆
- 会话管理（users / sessions）
- Skill 插件机制（`skills/` 目录）
- JWT 登录鉴权

并额外提供了一个完整的 `weather` 示例 Skill。

### 快速开始

- 使用 `uv` 安装依赖并启动：

```bash
uv sync
# 方式一：按配置文件中的端口启动（推荐，端口在 config.yaml 的 server.port 中配置）
uv run python -m app

# 方式二：直接指定端口
uv run uvicorn app.main:app --reload --port 8000
```

- **端口与 host**：在 `app/config/config.yaml` 中可配置 `server.port`（默认 8000）、`server.host`（默认 `0.0.0.0`）。使用 `python -m app` 启动时会自动读取该配置。

启动后访问：

- 健康检查：`GET /health`
- API 文档：`/docs` 或 `/redoc`

请根据实际环境修改 `app/config/config.yaml` 中的数据库、LLM、Milvus、JWT、Skill、服务端口等配置。

---

### API 接口说明与调用示例

以下所有接口基础路径为：`http://localhost:8000`（或你部署的域名）。除「认证」模块外，其余接口均需在请求头中携带登录后获得的 JWT：`Authorization: Bearer <access_token>`。

#### 1. 健康检查（无需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 服务健康检查 |

**请求示例：**

```bash
curl -X GET http://localhost:8000/health
```

**响应示例：**

```json
{"status": "ok"}
```

---

#### 2. 认证（无需 token）

##### 2.1 用户注册

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册新用户，返回成功提示（不返回 token，需登录后获取）。无需 token。 |

**请求体（JSON）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**请求示例：**

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret123"}'
```

**成功响应（200）：**

```json
{
  "code": 200,
  "message": "注册成功"
}
```

**失败示例（400，用户名已存在）：**

```json
{"detail": "Username already exists"}
```

##### 2.2 用户登录

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 用户名密码登录，返回 JWT。无需 token。 |

**请求体（JSON）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**请求示例：**

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret123"}'
```

**成功响应（200）：**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**失败示例（400）：**

```json
{"detail": "Incorrect username or password"}
```

---

#### 3. 会话（需 token）

以下接口均需在请求头中携带：`Authorization: Bearer <access_token>`（使用登录返回的 `access_token`）。

##### 3.1 创建会话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/session` | 创建或复用当前用户的会话，返回 session_uuid。 |

**请求体：** 无（可不传 body）。

**请求示例：**

```bash
curl -X POST http://localhost:8000/api/session \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

**成功响应（200）：**

```json
{
  "session_uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

##### 3.2 清空会话记忆

| 方法 | 路径 | 说明 |
|------|------|------|
| DELETE | `/api/session/{session_uuid}/memory` | 清空指定会话在向量库中的记忆，仅限当前用户的会话。 |

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| session_uuid | string | 会话 UUID |

**请求示例：**

```bash
curl -X DELETE "http://localhost:8000/api/session/550e8400-e29b-41d4-a716-446655440000/memory" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**成功响应（200）：**

```json
{"status": "ok"}
```

---

#### 4. 对话（需 token）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 发送一条消息，由 Agent 调用工具并返回回复。需 token。 |

**请求体（JSON）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | 是 | 用户发送的消息内容 |
| session_uuid | string | 否 | 会话 UUID；不传则自动创建新会话并在响应中返回该 session_uuid |

**请求示例：**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "今天北京天气怎么样？", "session_uuid": "550e8400-e29b-41d4-a716-446655440000"}'
```

不指定会话（由服务端创建新会话）：

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

**成功响应（200）：**

```json
{
  "session_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "根据当前查询，北京今天晴，气温 15°C..."
}
```

---

#### 5. 技能列表（需 token）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/skill` | 获取当前配置的可用技能列表。需 token。 |

**请求示例：**

```bash
curl -X GET http://localhost:8000/api/skill \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**成功响应（200）：**

```json
{
  "skills": [
    {
      "name": "查询天气",
      "description": "查询指定城市的当前天气情况",
      "location": "./skills/weather/SKILL.md"
    }
  ]
}
```

若未配置技能或 `skills.json` 为空，则返回：`{"skills": []}`。

---

#### 常见错误与统一错误格式

接口异常时均返回统一结构的 JSON（由全局异常处理生成）。**code 为数字：200 表示成功，400/401/404/422/500 等表示失败。**

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 成功时为无此字段或 true，失败时为 `false` |
| code | number | 200 成功，400/401/404/422/500 等为失败（与 HTTP 状态码一致） |
| message | string | 可读说明 |
| detail | any | 可选，校验错误时为字段列表，其余可为 null |

**成功示例（如注册）：**

```json
{
  "code": 200,
  "message": "注册成功"
}
```

**错误响应示例：**

```json
{
  "success": false,
  "code": 400,
  "message": "Username already exists"
}
```

**参数校验失败（422）示例：**

```json
{
  "success": false,
  "code": 422,
  "message": "body.username: 字段不能为空",
  "detail": [...]
}
```

| HTTP 状态码 | code | 说明 |
|-------------|------|------|
| 200 | 200 | 成功。 |
| 400 | 400 | 请求参数错误或业务校验失败（如用户名已存在、账号密码错误）。 |
| 401 | 401 | 未携带 token、token 无效或已过期，需重新登录。 |
| 404 | 404 | 路径或资源不存在。 |
| 422 | 422 | 请求体格式不符合要求（缺少必填字段、类型错误）。 |
| 500 | 500 | 数据库错误或服务器内部错误。 |

---

### Milvus 相似度检索（TopK）

对话历史会以向量形式存储在 Milvus 的 `chat_memory` collection 中。检索时：

- 使用当前用户问题的文本计算 embedding；
- 在 `user_id + session_uuid` 条件下进行向量相似度 TopK 搜索；
- 将检索到的 TopK 历史对话片段拼接成“历史上下文”，与当前问题一起提供给 Agent，提升多轮对话效果。

### Weather 示例 Skill

示例 Skill 目录结构：

```text
skills/
  skills.json
  weather/
    SKILL.md
    scripts/
      analyze_weather.py
```

- `skills/skills.json` 中已预置：

```json
{
  "skills": [
    {
      "name": "查询天气",
      "description": "查询指定城市的当前天气情况",
      "location": "./skills/weather/SKILL.md"
    }
  ]
}
```

- `weather/SKILL.md`：说明该 Skill 的能力、使用场景和技术实现思路。
- `weather/scripts/analyze_weather.py`：提供一个示例函数 `get_weather(city: str)`，当前为本地模拟天气数据，你可以在此基础上接入真实天气 API（如和风天气、OpenWeatherMap 等）。


