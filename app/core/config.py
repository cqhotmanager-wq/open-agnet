# 应用配置：从 YAML 加载并校验，支持数据库、LLM、JWT、技能等

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """服务监听配置（host、port）。"""
    host: str = "0.0.0.0"
    port: int = 8000


class DatabaseConfig(BaseModel):
    """数据库连接配置。"""
    type: Literal["mysql", "postgresql"] = "mysql"
    host: str = "localhost"
    port: int = 3306
    username: str
    password: str
    dbname: str

    @property
    def sqlalchemy_url(self) -> str:
        """生成 SQLAlchemy 连接 URL。"""
        if self.type == "mysql":
            return f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.dbname}"
        return f"postgresql+psycopg2://{self.username}:{self.password}@{self.host}:{self.port}/{self.dbname}"


class LLMConfig(BaseModel):
    """大模型接口配置（如 OpenAI、DeepSeek 等）。"""
    # provider: 用于区分不同厂商（如 "openai"、"deepseek"），目前主要用于选择 base_url
    provider: str = "openai"
    # model: 具体模型名称，例如 openai 的 "gpt-4"，deepseek 的 "deepseek-chat"
    model: str = "gpt-4"
    # api_key: 对应厂商的 API Key
    api_key: str
    # base_url: 可选，OpenAI 兼容服务的地址，例如 DeepSeek: https://api.deepseek.com/v1
    base_url: str | None = None
    # temperature / max_tokens: 通用采样与长度控制参数
    temperature: float = 0.3
    max_tokens: int | None = None


class VectorStoreConfig(BaseModel):
    """向量库配置（如 Milvus），用于对话记忆等。"""
    type: Literal["milvus"] = "milvus"
    host: str = "localhost"
    port: int = 19530
    collection: str = "chat_memory"


class JWTConfig(BaseModel):
    """JWT 签发与校验配置。"""
    secret: str
    expire_minutes: int = 120
    algorithm: str = "HS256"


# 单个技能默认目录结构（root_path 下每个技能名一层目录）：
#   <skill_name>/
#     SKILL.md         # 技能定义与说明
#     scripts/         # 脚本程序
#     references/      # 文档
#     assets/          # 静态资源
SKILL_DEFAULT_SUBDIRS = ("scripts", "references", "assets")


class SkillConfig(BaseModel):
    """技能目录与扫描配置。"""
    root_path: str = "./skills"
    skill_json_path: str = "./skills/skills.json"
    scan_interval_seconds: int = 60


class AppConfig(BaseModel):
    """全局应用配置，对应 config.yaml 根结构。"""
    server: ServerConfig = Field(default_factory=lambda: ServerConfig())
    database: DatabaseConfig
    llm: LLMConfig
    vector_store: VectorStoreConfig
    jwt: JWTConfig
    skill: SkillConfig


_config_cache: Optional[AppConfig] = None


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """加载并解析配置文件，结果带缓存，未传路径时使用默认 config/config.yaml。"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if config_path is None:
        config_path = Path(__file__).resolve().parents[1] / "config" / "config.yaml"
    else:
        config_path = Path(config_path)

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # 兼容旧配置：若无 server 则使用默认 host/port
    if raw is not None and "server" not in raw:
        raw = {**raw, "server": {"host": "0.0.0.0", "port": 8000}}

    _config_cache = AppConfig(**raw)
    return _config_cache

