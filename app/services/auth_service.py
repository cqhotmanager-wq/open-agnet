# 认证服务：用户相关数据库操作（查询、创建）

from sqlalchemy.orm import Session

from app.models.user import User


class AuthService:
    """认证服务，封装用户表的增删改查。"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> User | None:
        """按用户名查询用户，不存在则返回 None。"""
        return self.db.query(User).filter(User.username == username).first()

    def get_by_id(self, user_id: int) -> User | None:
        """按用户 ID 查询用户，不存在则返回 None。"""
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, username: str, password_hash: str) -> User:
        """创建新用户并提交到数据库，返回刷新后的用户对象。"""
        user = User(username=username, password_hash=password_hash)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
