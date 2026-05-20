from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, Computed
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from pgvector.sqlalchemy import Vector
import secrets

from app.db.database import Base
from app.config import settings

# --- User related tables ---

class Users(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[str] = mapped_column(unique=True, index=True)
    username: Mapped[str] = mapped_column(index=True)
    email: Mapped[Optional[str]] = mapped_column(unique=True, index=True)
    github_token: Mapped[Optional[str]]
    has_repo_access: Mapped[bool] = mapped_column(default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
class Sessions(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    title: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
class Messages(Base):
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    role: Mapped[str]
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

class ShareableLinks(Base):
    __tablename__ = "shareable_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
# --- Repository related tables ---    

class Repositories(Base):
    __tablename__ = "repositories"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str]
    name: Mapped[str]
    url: Mapped[str] = mapped_column(unique=True)
    commit_hash: Mapped[Optional[str]]
    status: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
class Files(Base):
    __tablename__ = "files"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    file_path: Mapped[str]
    language: Mapped[str]
    size_bytes: Mapped[int]
    
class CodeChunks(Base):
    __tablename__ = "code_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), index=True)
    chunk_type: Mapped[str]
    name: Mapped[Optional[str]]
    content: Mapped[str] = mapped_column(Text)
    start_line: Mapped[int]
    end_line: Mapped[int]
    embedding = mapped_column(Vector(settings.embedding_dimensions), nullable=True)
    content_tsv = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', content)", persisted=True),
        nullable=True,
    )

class RevokedTokens(Base):
    __tablename__ = "revoked_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(index=True)
    