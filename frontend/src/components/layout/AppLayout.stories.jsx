import { useState } from "react";
import AppLayout from "./AppLayout";

// ── Mock data ──────────────────────────────────────────────────────────────

const SESSIONS = [
  {
    id: 1,
    title: "Auth service review",
    repoName: "acme/auth-service",
    status: "completed",
    lastActive: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    isActive: true,
  },
  {
    id: 2,
    title: "Frontend onboarding",
    repoName: "acme/frontend",
    status: "processing",
    lastActive: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    isActive: false,
  },
  {
    id: 3,
    title: "Data pipeline docs",
    repoName: "acme/data-pipeline",
    status: "failed",
    lastActive: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    isActive: false,
  },
];

const FILES = [
  { id: 1, file_path: "app/__init__.py", language: "python", size_bytes: 0 },
  { id: 2, file_path: "app/main.py", language: "python", size_bytes: 1240 },
  { id: 3, file_path: "app/config.py", language: "python", size_bytes: 890 },
  {
    id: 4,
    file_path: "app/api/dependencies.py",
    language: "python",
    size_bytes: 600,
  },
  {
    id: 5,
    file_path: "app/api/routes/auth.py",
    language: "python",
    size_bytes: 1800,
  },
  {
    id: 6,
    file_path: "app/db/models.py",
    language: "python",
    size_bytes: 2100,
  },
  { id: 7, file_path: "README.md", language: "markdown", size_bytes: 2400 },
];

const MOCK_CONTENTS = {
  "app/__init__.py": "",
  "app/main.py": `from fastapi import FastAPI
from app.api.routes import auth, sessions
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="Codebase Onboarding Agent")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])


@app.get("/health")
async def health():
    return {"status": "ok"}
`,
  "app/config.py": `from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    github_token: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
`,
  "app/api/dependencies.py": `from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.db.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await db.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user
`,
  "app/api/routes/auth.py": `from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.utility.auth import verify_password, create_access_token

router = APIRouter()


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await User.get_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}
`,
  "app/db/models.py": `from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("Session", back_populates="user")

    @classmethod
    async def get_by_email(cls, db: AsyncSession, email: str):
        result = await db.execute(select(cls).where(cls.email == email))
        return result.scalar_one_or_none()
`,
  "README.md": `# Codebase Onboarding Agent

An AI-powered tool that helps developers quickly understand unfamiliar codebases.

## Features

- GitHub repository ingestion
- RAG-based chat over your codebase
- File tree explorer with syntax highlighting
- Session management

## Quick Start

\`\`\`bash
docker compose up -d
cd backend && fastapi dev app/main.py
cd frontend && npm run dev
\`\`\`
`,
};

const t = (minsAgo) => new Date(Date.now() - minsAgo * 60 * 1000).toISOString();

const INITIAL_MESSAGES = [
  {
    id: 1,
    role: "user",
    content: "What does the authentication flow look like?",
    createdAt: t(10),
  },
  {
    id: 2,
    role: "assistant",
    content: `Authentication uses **JWT tokens**:

1. Client POSTs credentials to \`/auth/login\`
2. Server verifies and returns a signed JWT
3. Client sends the token in the \`Authorization\` header

Click **app/api/dependencies.py** in the file tree to see the \`get_current_user\` dependency.`,
    createdAt: t(9),
  },
];

// ── Interactive wrapper ────────────────────────────────────────────────────

function InteractiveAppLayout() {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = (text) => {
    if (!text.trim()) return;
    setMessages((prev) => [
      ...prev,
      {
        id: prev.length + 1,
        role: "user",
        content: text,
        createdAt: new Date().toISOString(),
      },
    ]);
    setIsLoading(true);
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: prev.length + 1,
          role: "assistant",
          content: "This is a simulated assistant response.",
          createdAt: new Date().toISOString(),
        },
      ]);
      setIsLoading(false);
    }, 1200);
  };

  const getFileContent = async (file) => {
    return (
      MOCK_CONTENTS[file.file_path] ??
      `# ${file.file_path}\n# (no mock content)`
    );
  };

  return (
    <AppLayout
      sessions={SESSIONS}
      repoName="acme/auth-service"
      files={FILES}
      messages={messages}
      onSend={handleSend}
      isLoading={isLoading}
      getFileContent={getFileContent}
    />
  );
}

// ── Stories ───────────────────────────────────────────────────────────────

export default {
  title: "Components/Layout/AppLayout",
  component: AppLayout,
  parameters: { layout: "fullscreen" },
};

export const Default = {
  render: () => <InteractiveAppLayout />,
};

export const NoSessions = {
  render: () => <InteractiveAppLayout />,
  args: { sessions: [] },
};
