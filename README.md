# 智能体平台（FastAPI + LangChain）

## 一、系统介绍

本项目是一个基于 **FastAPI** + **LangChain** 的智能体平台，支持多轮对话、会话记忆、技能插件与工具调用，主要能力包括：

| 能力 | 说明 |
|------|------|
| **用户与鉴权** | 用户注册、登录；JWT 鉴权，除认证接口外均需携带 Token |
| **会话周期** | 每次访问 chat 可创建新会话或复用已有会话，`session_uuid` 唯一标识一轮对话，整轮上下文一致 |
| **记忆与上下文** | SQL 存完整聊天与会话摘要，Milvus 存长期向量记忆；通过 **user_id + session_uuid** 在向量库中定位本次会话，通过 **user_id** 可查用户全部会话 |
| **对话流程** | 构建上下文（系统提示 + 技能 + 最近历史 + 摘要 + 向量检索）→ 拼成 Prompt → 调用 LLM + 工具 → 写入聊天并可选更新摘要 |
| **技能插件** | 从 `skills/skills.json` 与各技能目录下的 `SKILL.md` 加载能力描述，注入系统提示，供 Agent 按文档执行 |
| **可配置** | 数据库（MySQL/PostgreSQL）、LLM、Embedding、Milvus、JWT、服务端口等均在 `app/config/config.yaml` 中配置 |

技术栈概览：

- **Web**：FastAPI，CORS 开放，统一异常与错误码
- **数据库**：SQLAlchemy + MySQL/PostgreSQL（用户、会话、聊天记录、会话摘要）
- **向量库**：Milvus（长期记忆集合 `agent_memory`，按 user_id + session_uuid 检索）
- **LLM/Embedding**：OpenAI 兼容接口（如 DeepSeek），通过配置文件切换

---

## 二、数据库创建与初始化

### 2.1 使用 MySQL 初始化脚本（推荐）

库名需与 `config.yaml` 中 `database.dbname` 一致（默认 `agent_platform`）。

```bash
# 使用 MySQL 客户端执行
mysql -u root -p < scripts/init_mysql.sql
```

脚本会：

- 创建数据库 `agent_platform`（若不存在）
- 创建表：`users`、`sessions`、`chat_message`、`conversation_summary`

表说明：

| 表名 | 说明 |
|------|------|
| users | 用户表：id、username、password_hash、created_at |
| sessions | 会话表：id、user_id、session_uuid（唯一）、is_active、created_at |
| chat_message | 聊天记录：id、session_uuid、role、content、created_at |
| conversation_summary | 会话摘要：session_uuid（主键）、summary、updated_at |

### 2.2 使用应用自动建表

若不执行 SQL 脚本，应用启动时会根据 ORM 模型执行 `Base.metadata.create_all(bind=engine)`，自动创建上述表（需数据库已存在且连接正常）。若使用 PostgreSQL，请先手动创建数据库，表结构由 SQLAlchemy 生成。

### 2.3 Milvus

- 应用首次使用时会自动创建 Milvus 集合 **agent_memory**（含 user_id、session_uuid、text、embedding、type、timestamp）。
- 请先启动 Milvus 服务，并在 `config.yaml` 中配置 `vector_store` 与 `embedding`（如 host、port、dimensions）。

---

## 三、快速开始

1. **安装依赖并启动**

```bash
uv sync
# 按 config.yaml 中的 server.port 启动（推荐）
uv run python -m app

# 或指定端口
uv run uvicorn app.main:app --reload --port 8000
```

2. **配置**  
   修改 `app/config/config.yaml` 中的数据库、LLM、Milvus、JWT、技能路径、服务端口等。

3. **访问**  
   - 健康检查：`GET /health`  
   - API 文档：`/docs` 或 `/redoc`

---

## 四、接口说明与调用示例

基础路径：`http://localhost:8000`（或你的部署域名）。除「认证」外，其余接口均需在请求头中携带：`Authorization: Bearer <access_token>`。

### 4.1 健康检查（无需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 服务健康检查，用于探活或负载均衡 |

**请求示例：**

```bash
curl -X GET http://localhost:8000/health
```

**响应示例：** `{"status": "ok"}`

---

### 4.2 认证（无需 token）

#### 4.2.1 用户注册

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册新用户，成功返回提示；不返回 token，需再调用登录。 |

**请求体（JSON）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**示例：**

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret123"}'
```

**成功（200）：** `{"code": 200, "message": "注册成功"}`  
**失败（400）：** 如 `{"detail": "Username already exists"}`

#### 4.2.2 用户登录

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 用户名密码登录，返回 JWT。 |

**请求体（JSON）：** username、password 必填。

**示例：**

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret123"}'
```

**成功（200）：** `{"access_token": "eyJ...", "token_type": "bearer"}`  
**失败（400）：** 如 `{"detail": "Incorrect username or password"}`

---

### 4.3 会话（需 token）

以下接口均需：`Authorization: Bearer <access_token>`。

#### 4.3.1 查询当前用户所有会话

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/session` | 按当前用户 id 查询该用户所有会话，按创建时间倒序。 |

**请求示例：**

```bash
curl -X GET http://localhost:8000/api/session \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**成功响应（200）：**

```json
{
  "sessions": [
    {
      "session_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "is_active": true,
      "created_at": "2025-03-05T10:00:00"
    }
  ]
}
```

#### 4.3.2 创建会话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/session` | 为当前用户创建新会话（或复用逻辑由实现决定），返回 session_uuid。 |

**请求体：** 无（可不传 body）。

**示例：**

```bash
curl -X POST http://localhost:8000/api/session \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

**成功（200）：** `{"session_uuid": "550e8400-e29b-41d4-a716-446655440000"}`

#### 4.3.3 清空会话记忆

| 方法 | 路径 | 说明 |
|------|------|------|
| DELETE | `/api/session/{session_uuid}/memory` | 清空指定会话的记忆（SQL 聊天记录与摘要 + Milvus 向量），仅限当前用户的会话。 |

**路径参数：** `session_uuid`（string）。

**示例：**

```bash
curl -X DELETE "http://localhost:8000/api/session/550e8400-e29b-41d4-a716-446655440000/memory" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**成功（200）：** `{"status": "ok"}`  
**会话不存在或非当前用户（404）：** `{"detail": "Session not found"}`

---

### 4.4 对话（需 token）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 发送一条消息，由 Agent 结合上下文（最近历史、摘要、向量检索）调用 LLM 与工具后返回回复。 |

**请求体（JSON）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | 是 | 用户消息内容 |
| session_uuid | string | 否 | 会话 UUID；不传或传空则创建新会话周期，响应中返回新 session_uuid，后续请求应携带以保持同一上下文 |

**请求示例（新会话）：**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

**请求示例（延续已有会话）：**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "今天北京天气怎么样？", "session_uuid": "550e8400-e29b-41d4-a716-446655440000"}'
```

**成功响应（200）：**

```json
{
  "session_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "根据当前查询，北京今天晴，气温 15°C..."
}
```

---

### 4.5 技能列表（需 token）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/skill` | 获取当前配置的可用技能列表（来自 skills/skills.json 及 SKILL.md 配置）。 |

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

未配置或为空时返回：`{"skills": []}`。

---

### 4.6 常见错误与统一错误格式

接口异常时返回统一 JSON 结构，**code 为数字**：200 成功，400/401/404/422/500 等为失败。

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 失败时为 false |
| code | number | 与 HTTP 状态码一致 |
| message | string | 可读说明 |
| detail | any | 可选，如校验错误详情 |

| HTTP 状态码 | code | 说明 |
|-------------|------|------|
| 200 | 200 | 成功 |
| 400 | 400 | 参数或业务错误（如用户名已存在、密码错误） |
| 401 | 401 | 未携带 token、token 无效或过期 |
| 404 | 404 | 资源不存在（如会话不存在） |
| 422 | 422 | 请求体验证失败（缺少必填、类型错误） |
| 500 | 500 | 数据库或服务器内部错误 |

---

## 五、记忆与上下文说明

- **SQL**：完整聊天写入 `chat_message`，会话摘要写入 `conversation_summary`；最近 N 条历史与摘要均从 SQL 查询。
- **Milvus**：长期记忆写入集合 **agent_memory**，按 **user_id + session_uuid** 过滤，用于向量相似度检索，结果作为「Retrieved Memory」拼入 Prompt。
- **Prompt 顺序**：System → User profile → Conversation summary → Recent history → Retrieved memory → Current question。

---

## 六、使用场景

| 场景 | 说明 |
|------|------|
| **多轮对话助手** | 用户登录后，首次发消息不传 session_uuid，拿到返回的 session_uuid 后后续请求都带该 id，实现同一会话内连续多轮对话与上下文一致。 |
| **多会话管理** | 通过 `GET /api/session` 查看当前用户所有会话列表，便于前端展示「历史会话」或选择继续某轮对话。 |
| **清空单轮记忆** | 用户希望「重新开始」某轮对话时，调用 `DELETE /api/session/{session_uuid}/memory` 清空该会话的聊天、摘要与向量记忆。 |
| **技能扩展** | 在 `skills/` 下新增技能目录与 `SKILL.md`，并在 `skills.json` 中注册，Agent 即可在系统提示中看到新技能并按文档调用工具。 |
| **内网/私有化 LLM** | 在 config.yaml 中配置 LLM、Embedding 的 base_url 与 api_key，对接内网或私有化部署的 OpenAI 兼容服务。 |
| **健康与部署** | 通过 `GET /health` 做负载均衡探活或监控；根据需求调整 server.port、CORS、JWT 过期时间等。 |

---

## 七、Weather 示例 Skill

目录结构示例：

```text
skills/
  skills.json
  weather/
    SKILL.md
    scripts/
      analyze_weather.py
```

- `skills.json` 中配置技能名称、描述与 `location`（如 `./skills/weather/SKILL.md`）。
- `SKILL.md` 描述该技能能力与使用方式；Agent 会将该内容注入系统提示。
- `scripts/analyze_weather.py` 可提供如 `get_weather(city)` 等实现，当前可为本地模拟，后续可接入真实天气 API。

---

## 八、项目结构简要说明

| 目录/文件 | 说明 |
|-----------|------|
| app/main.py | FastAPI 入口、路由挂载、全局异常处理、建表 |
| app/core/ | 配置、数据库、鉴权、异常、回调等基础能力 |
| app/models/ | 用户、会话、聊天记录、会话摘要、请求/响应模型 |
| app/api/ | 认证、会话、对话、技能等 HTTP 接口 |
| app/repositories/ | 聊天记录、会话摘要的 SQL 仓储 |
| app/manager/ | 统一记忆管理（SQL + Milvus，读写与摘要更新） |
| app/context/ | 上下文数据构建（系统提示、历史、摘要、检索记忆） |
| app/prompt/ | 将 ContextData 格式化为 LLM 消息列表 |
| app/services/ | 认证、会话、技能、Agent 流水线、Legacy 记忆服务 |
| app/tools/ | LangChain 工具（文件、数据库、网页、搜索等） |
| app/config/config.yaml | 服务、数据库、LLM、向量库、JWT、技能等配置 |
| scripts/init_mysql.sql | MySQL 建库建表脚本 |

代码中已补充中文注释，便于阅读与二次开发。
