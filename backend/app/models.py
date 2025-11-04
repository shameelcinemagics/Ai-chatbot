from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all,delete")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    jwt_id = Column(String, unique=True, nullable=False, index=True)
    revoked = Column(Boolean, nullable=False, server_default="false")
    replaced_by = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    ip = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

    user = relationship("User", back_populates="refresh_tokens")
