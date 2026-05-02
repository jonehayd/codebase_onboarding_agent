from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# --- Auth ---

class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    has_repo_access: bool
    created_at: datetime


# --- Sessions ---

class CreateSessionOut(BaseModel):
    session_id: int
    repo_id: int
    owner: str
    name: str
    status: str
    created_at: datetime


class SessionSummary(BaseModel):
    session_id: int
    title: Optional[str] = None
    repo_id: int
    owner: str
    name: str
    url: str
    status: str
    created_at: datetime
    last_active_at: datetime


class ListSessionsOut(BaseModel):
    sessions: list[SessionSummary]


class RepoDetail(BaseModel):
    id: int
    owner: str
    name: str
    url: str
    status: str
    commit_hash: Optional[str] = None
    created_at: datetime
    file_count: int
    chunk_count: int


class SessionDetail(BaseModel):
    session_id: int
    title: Optional[str] = None
    created_at: datetime
    last_active_at: datetime
    repo: RepoDetail


class PatchSessionOut(BaseModel):
    session_id: int
    title: str


class SessionStatusOut(BaseModel):
    session_id: int
    repo_id: int
    status: str
    stage: str
    percent: int
    files_total: int
    file_count: int
    vector_count: int
    elapsed_seconds: Optional[int] = None
    commit_hash: Optional[str] = None


class FreshnessOut(BaseModel):
    is_stale: bool
    stored_commit: Optional[str] = None
    latest_commit: str


class ReingestOut(BaseModel):
    session_id: int
    repo_id: int
    status: str


class FileItem(BaseModel):
    id: int
    file_path: str
    language: str
    size_bytes: int


class ListFilesOut(BaseModel):
    session_id: int
    files: list[FileItem]


class SearchFilesOut(BaseModel):
    session_id: int
    query: str
    files: list[FileItem]


class FileContentOut(BaseModel):
    id: int
    file_path: str
    language: str
    content: str


class ShareLinkOut(BaseModel):
    token: str
    url: str


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime


class HistoryOut(BaseModel):
    messages: list[MessageOut]
    total: int
    limit: int
    offset: int


# --- Share ---

class ShareInfoOut(BaseModel):
    session_id: int
    repo_id: int
    owner: str
    name: str
    url: str
    status: str
