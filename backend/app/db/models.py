from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from pgvector.sqlalchemy import Vector
from app.db.database import Base
from app.config import settings

# --- User related tables ---

class Users(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[str] = mapped_column(unique=True, index=True)
    username: Mapped[str] = mapped_column(index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    github_token: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
class Sessions(Base):
    __tablename__ = "sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
class Messages(Base):
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    role: Mapped[str]
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
# --- Repository related tables ---    

class Repositories(Base):
    __tablename__ = "repositories"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str]
    name: Mapped[str]
    url: Mapped[str] = mapped_column(unique=True)
    commit_hash: Mapped[str]
    status: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
# Association table for many-to-many relationship between users and repositories
class UserRepositories(Base):
    __tablename__ = "user_repositories"
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), primary_key=True)
    
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
    