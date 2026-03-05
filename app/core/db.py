# 数据库连接与会话：引擎、Session 工厂、请求级 get_db

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import load_config


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类，所有模型继承此类。"""
    pass


config = load_config()

# 根据 config 创建引擎，pool_pre_ping 保证连接可用
engine = create_engine(
    config.database.sqlalchemy_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI 依赖：每个请求一个 DB 会话，请求结束后关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

