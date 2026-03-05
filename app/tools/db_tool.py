# 访问 MySQL 等数据库的工具（执行只读或受控的 SQL，使用应用配置的连接）

from typing import Optional, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import load_config
from app.core.db import SessionLocal

config = load_config()


class RunSqlInput(BaseModel):
    """执行 SQL 入参。"""
    query: str = Field(description="要执行的 SQL 语句，建议仅使用 SELECT 查询；写入操作请谨慎")
    database: Optional[str] = Field(
        default=None,
        description="可选，指定数据库名；不填则使用配置中的 dbname",
    )


class RunSqlTool(BaseTool):
    name: str = "run_sql"
    description: str = "使用应用配置的数据库连接执行 SQL（如 MySQL）。主要用于 SELECT 查询，慎用写操作。"
    args_schema: Type[RunSqlInput] = RunSqlInput

    def _run(self, query: str, database: Optional[str] = None) -> str:
        db: Session = SessionLocal()
        try:
            if database and config.database.type == "mysql":
                db.execute(text(f"USE `{database}`"))
            result = db.execute(text(query))
            rows = result.fetchall()
            if not rows:
                return "查询结果为空。"
            # 简单表格化：列名 + 行（从第一行取列名以兼容不同驱动）
            keys = list(rows[0]._mapping.keys())
            lines = ["\t".join(keys)]
            for row in rows:
                lines.append("\t".join(str(row._mapping[k]) for k in keys))
            return "\n".join(lines)
        except Exception as e:
            return f"执行 SQL 失败: {e}"
        finally:
            db.close()

    async def _arun(self, query: str, database: Optional[str] = None) -> str:
        return self._run(query=query, database=database)
