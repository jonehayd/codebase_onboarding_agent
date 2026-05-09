import FileView from "./FileView";

const PY_CONTENT = `from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.routes import auth, sessions

app = FastAPI(title="Codebase Onboarding Agent")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
`;

const TS_CONTENT = `import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
`;

const JSON_CONTENT = `{
  "name": "vite-project",
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "storybook": "storybook dev -p 6006"
  },
  "dependencies": {
    "react": "^19.2.5",
    "react-dom": "^19.2.5",
    "tailwindcss": "^4.2.4"
  }
}
`;

const MD_CONTENT = `# Codebase Onboarding Agent

An AI-powered tool for exploring and understanding codebases.

## Features

- GitHub repository ingestion
- Semantic code search
- Conversational Q&A over your codebase

## Getting Started

\`\`\`bash
docker compose up -d
\`\`\`
`;

const Viewport = ({ children }) => (
  <div className="bg-base h-screen w-160 flex flex-col">{children}</div>
);

export default {
  title: "Components/Files/FileView",
  component: FileView,
};

export const Python = {
  render: () => (
    <Viewport>
      <FileView filename="main.py" content={PY_CONTENT} />
    </Viewport>
  ),
};

export const TypeScript = {
  render: () => (
    <Viewport>
      <FileView filename="utils.ts" content={TS_CONTENT} />
    </Viewport>
  ),
};

export const JSON = {
  render: () => (
    <Viewport>
      <FileView filename="package.json" content={JSON_CONTENT} />
    </Viewport>
  ),
};

export const Markdown = {
  render: () => (
    <Viewport>
      <FileView filename="README.md" content={MD_CONTENT} />
    </Viewport>
  ),
};

export const Empty = {
  render: () => (
    <Viewport>
      <FileView filename="empty.py" content="" />
    </Viewport>
  ),
};
