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
uv run uvicorn app.main:app --reload
```

启动后访问：

- 健康检查：`GET /health`
- API 文档：`/docs` 或 `/redoc`

请根据实际环境修改 `app/config/config.yaml` 中的数据库、LLM、Milvus、JWT、Skill 等配置。

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


