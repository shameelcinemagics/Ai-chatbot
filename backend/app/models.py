from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from .db import Base


class User(Base):
__tablename__ = 'users'
id = Column(Integer, primary_key=True, index=True)
username = Column(String, unique=True, nullable=False)
password_hash = Column(String, nullable=False)
is_admin = Column(Boolean, default=False)
created_at = Column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
__tablename__ = 'refresh_tokens'
id = Column(Integer, primary_key=True, index=True)
user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
token = Column(String, nullable=False, unique=True)
expires_at = Column(Integer, nullable=False)
revoked = Column(Boolean, default=False)