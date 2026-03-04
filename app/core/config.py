from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    type: Literal["mysql", "postgresql"] = "mysql"
    host: str = "localhost"
    port: int = 3306
    username: str
    password: str
    dbname: str

    @property
    def sqlalchemy_url(self) -> str:
        if self.type == "mysql":
            return f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.dbname}"
        return f"postgresql+psycopg2://{self.username}:{self.password}@{self.host}:{self.port}/{self.dbname}"


class LLMConfig(BaseModel):
    provider: Literal["openai"] = "openai"
    model: str = "gpt-4"
    api_key: str


class VectorStoreConfig(BaseModel):
    type: Literal["milvus"] = "milvus"
    host: str = "localhost"
    port: int = 19530
    collection: str = "chat_memory"


class JWTConfig(BaseModel):
    secret: str
    expire_minutes: int = 120
    algorithm: str = "HS256"


class SkillConfig(BaseModel):
    root_path: str = "./skills"
    skill_json_path: str = "./skills/skills.json"
    scan_interval_seconds: int = 60


class AppConfig(BaseModel):
    database: DatabaseConfig
    llm: LLMConfig
    vector_store: VectorStoreConfig
    jwt: JWTConfig
    skill: SkillConfig


_config_cache: Optional[AppConfig] = None


def load_config(config_path: str | Path | None = None) -> AppConfig:
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if config_path is None:
        config_path = Path(__file__).resolve().parents[1] / "config" / "config.yaml"
    else:
        config_path = Path(config_path)

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    _config_cache = AppConfig(**raw)
    return _config_cache

