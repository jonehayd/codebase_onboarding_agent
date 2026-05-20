# Codebase Onboarding Agent

**Project Overview** | Hayden Jones | hjones.dev | github.com/jonehayd

---

## What It Is

A full-stack web application that lets developers understand an unfamiliar GitHub repository by asking questions about it in plain English. A user logs in with GitHub, pastes a public repository URL, and the system ingests and indexes the codebase. From there they can ask questions like:

- What are the API endpoints and what do they do?
- How does authentication work in this project?
- What would I need to change to add a new database model?
- How do I run this project locally?
- What third-party services does this project depend on?

The goal is not to generate static documentation. It is to give developers an interactive way to build a mental model of a codebase quickly, without reading every file manually.

**Live at:** https://codebaseonboardingagent.hjones.dev/

---

## Problem Being Solved

Every developer has experienced the pain of joining a project mid-stream or inheriting someone else's code. Existing tools either require an IDE plugin installed locally, generate static documentation that goes stale, or require the full codebase to fit in a context window. There is no standalone web tool that lets you paste a GitHub URL and immediately start asking intelligent questions about the code.

This tool is aimed at:

- New developers onboarding to an unfamiliar codebase
- Team leads sharing codebase context with non-technical stakeholders
- Developers auditing or reviewing an open source project before adopting it
- Freelancers and contractors getting up to speed on a client codebase quickly

---

## Tech Stack

| Layer            | Tools                                                     |
| ---------------- | --------------------------------------------------------- |
| Frontend         | React 19, TypeScript, Vite, TailwindCSS, TanStack Query   |
| Backend          | Python 3.12, FastAPI, SQLAlchemy, Alembic                 |
| LLM              | Anthropic Claude (claude-haiku-4-5)                       |
| Code Parsing     | Tree-sitter with grammars for Python, JS, TS, Java, Go    |
| Embeddings       | OpenAI text-embedding-3-small (1536 dimensions)           |
| Database         | PostgreSQL 16 with pgvector extension                     |
| Search           | Hybrid BM25 + semantic search with Reciprocal Rank Fusion |
| Cache / State    | Redis 7                                                   |
| Repo Ingestion   | GitHub REST API via PyGithub                              |
| Monitoring       | Sentry                                                    |
| Hosting          | AWS EC2 (backend), AWS RDS (database), Vercel (frontend)  |
| Reverse Proxy    | Nginx                                                     |
| Containerization | Docker, Docker Compose                                    |

---

## System Architecture

### Repo Ingestion Pipeline

When a user submits a GitHub URL, the backend fetches the repository file tree via the GitHub API using a single git tree call, then downloads each file concurrently using a pool of async workers. Files are filtered by size, extension, and type to skip binaries, lock files, and build artifacts.

Each code file is parsed with Tree-sitter to extract structured units: functions, classes, methods, and imports. These are chunked intelligently based on code structure rather than fixed character counts. Important configuration files like `package.json`, `requirements.txt`, `Dockerfile`, and `README.md` are tagged as pinned and always included in retrieval regardless of relevance scoring.

Chunks are embedded in batches using OpenAI's embedding model and stored in PostgreSQL with pgvector. A `content_tsv` column on each chunk is computed automatically on insert for full-text search. The repository's latest commit hash is stored alongside the data so the system can detect when a repo has changed and skip re-ingestion if nothing has been updated.

### Query and Retrieval Pipeline

When a user asks a question, Claude first expands it into two or three sub-queries with slightly different phrasing. All queries are embedded and used to run both a vector similarity search and a BM25 keyword search against the chunk table. The two ranked result sets are merged using Reciprocal Rank Fusion, which rewards chunks that rank highly in both searches. Pinned files are appended regardless of score.

The assembled chunks plus the conversation history are used to build a prompt which is sent to Claude. The response streams back via Server-Sent Events and is displayed in the frontend as it arrives.

### Sessions and Sharing

Each ingested repository is associated with a session belonging to a specific user. Sessions persist chat history and can be renamed. Users can generate a shareable link for any session, which gives anonymous read-only access to the same chat and file browser without requiring an account.

---

## Features

### Core (Implemented)

- GitHub OAuth authentication with optional private repo scope
- Session management with history, renaming, and deletion
- Async repository ingestion with real-time progress tracking and cancellation support
- Tree-sitter code parsing for Python, JavaScript, TypeScript, Java, and Go
- Hybrid BM25 and semantic search with Reciprocal Rank Fusion
- Streaming chat via Server-Sent Events
- Persistent conversation history per session
- Shareable anonymous links with rate-limited chat
- File browser and raw file viewing via GitHub API
- Query expansion via Claude before retrieval
- Commit hash freshness checking and re-ingestion support
- Rate limiting on chat endpoints (30 requests per day for authenticated users)

### Not Yet Implemented

- Export conversation as Markdown or PDF
- Multi-repo mode (ask questions across multiple repos at once)
- Response citations showing which files were used to generate an answer

---

## What Makes It Different

Tools like GitHub Copilot require a locally cloned repository and an IDE. This app is standalone, nothing to install, and works from a URL in any browser. The Tree-sitter parsing layer means the system understands code structure rather than treating source files as raw text, which produces cleaner chunks and more precise retrieval. The hybrid search approach combines keyword matching and semantic similarity, making it more reliable than either approach alone.

---

## Database Schema

**Users and Sessions**

- `Users` stores GitHub user info and auth tokens
- `Sessions` links a user to an indexed repository and tracks activity
- `Messages` stores the full chat history for each session
- `ShareableLinks` holds the token and metadata for anonymous access links
- `RevokedTokens` is a blocklist for logged-out JWT tokens

**Repository and Code**

- `Repositories` stores repo metadata and the latest indexed commit hash
- `Files` stores each file's path, language, and size
- `CodeChunks` stores individual code units with their embedding vector, full-text search vector, and source location

---

## API Endpoints

**Authentication**

- `GET /auth/github` — Start GitHub OAuth flow
- `GET /auth/github/callback` — Handle OAuth callback
- `GET /auth/me` — Get current user profile
- `GET /auth/repos` — List user's GitHub repositories
- `POST /auth/logout` — Revoke the current JWT token

**Sessions**

- `POST /sessions` — Create a session and start ingestion
- `GET /sessions` — List all sessions for the current user
- `GET /sessions/{id}` — Get session details
- `PATCH /sessions/{id}` — Rename a session
- `DELETE /sessions/{id}` — Delete a session
- `GET /sessions/{id}/status` — Get ingestion status and progress
- `POST /sessions/{id}/cancel` — Cancel an in-progress ingestion
- `GET /sessions/{id}/freshness` — Check whether the repo has new commits
- `POST /sessions/{id}/reingest` — Trigger a fresh ingestion
- `POST /sessions/{id}/chat` — Stream a chat response (SSE)
- `GET /sessions/{id}/history` — Get paginated chat history
- `GET /sessions/{id}/files` — List indexed files
- `GET /sessions/{id}/files/{file_id}` — Fetch a file's content from GitHub
- `POST /sessions/{id}/share` — Create a shareable link
- `DELETE /sessions/{id}/share` — Revoke the shareable link

**Shareable Links (no auth required)**

- `GET /share/{token}` — Get repo metadata for a shared session
- `POST /share/{token}/chat` — Stream a chat response on a shared session (SSE)
- `GET /share/{token}/history` — Get shared session chat history
- `GET /share/{token}/files` — List files for a shared session
- `GET /share/{token}/files/{file_id}` — Fetch a file's content

**Health**

- `GET /health` — Liveness check
