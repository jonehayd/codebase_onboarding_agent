# Codebase Onboarding Agent

**Project Plan** | Hayden Jones | Last updated: May 2026

---

## Status Key

| Symbol | Meaning     |
| ------ | ----------- |
| ⬜     | Not Started |
| 🔵     | In Progress |
| ✅     | Done        |
| 🔴     | Blocked     |

---

## Timeline Summary

| Phase | Description               | Status         |
| ----- | ------------------------- | -------------- |
| 1     | Repo Ingestion Pipeline   | ✅ Complete    |
| 2     | Query and Retrieval (RAG) | ✅ Complete    |
| 3     | FastAPI Backend Endpoints | ✅ Complete    |
| 4     | React Frontend            | ✅ Complete    |
| 5     | AWS Deployment            | ✅ Complete    |
| 6     | Polish and Stretch Goals  | 🔵 In Progress |

---

## Phase 1 — Repo Ingestion Pipeline

**Status: Complete**

| Status | Task                                                                  | Notes                                                                                      |
| ------ | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| ✅     | Set up Python project structure and virtual environment               |                                                                                            |
| ✅     | Install and configure PyGithub for GitHub API access                  |                                                                                            |
| ✅     | Implement repo fetching via git tree API                              | Used single git tree call instead of recursive get_contents for better performance         |
| ✅     | Concurrent file downloads with async worker pool                      | 16 parallel workers                                                                        |
| ✅     | Install Tree-sitter and language grammars (Python, TS, JS, Java, Go)  |                                                                                            |
| ✅     | Build AST parser to extract functions, classes, methods, and imports  | Separate parser per language                                                               |
| ✅     | Design structure-based chunking                                       | Functions and classes are their own chunks; line-based fallback for unsupported file types |
| ✅     | Set up PostgreSQL with pgvector extension                             |                                                                                            |
| ✅     | Design and implement database schema                                  |                                                                                            |
| ✅     | Implement embedding generation with OpenAI text-embedding-3-small     | Batched in groups of 300                                                                   |
| ✅     | Store chunks and embeddings in pgvector with tsvector column for BM25 |                                                                                            |
| ✅     | Commit hash caching to skip re-ingestion on unchanged repos           |                                                                                            |
| ✅     | File filtering by size, extension, and type                           | Skip binaries, lock files, and build artifacts                                             |
| ✅     | Write unit tests for parser and chunking logic                        |                                                                                            |

---

## Phase 2 — Query and Retrieval (RAG)

**Status: Complete**

| Status | Task                                                       | Notes                                                                        |
| ------ | ---------------------------------------------------------- | ---------------------------------------------------------------------------- |
| ✅     | Implement query embedding pipeline                         |                                                                              |
| ✅     | Build hybrid search combining BM25 and semantic similarity | Built custom hybrid search instead of LlamaIndex                             |
| ✅     | Implement Reciprocal Rank Fusion to merge result sets      |                                                                              |
| ✅     | Query expansion via Claude before retrieval                | Generates 2 to 3 sub-queries per question                                    |
| ✅     | Pinned file strategy                                       | package.json, requirements.txt, Dockerfile, README always included           |
| ✅     | Design and implement prompt builder                        | Includes repo context, file list, retrieved chunks, and conversation history |
| ✅     | Integrate Anthropic Claude API for completions             |                                                                              |
| ✅     | Implement streaming response support via SSE               |                                                                              |
| ✅     | Maintain conversation history per session                  | Saved to database and passed as context                                      |

---

## Phase 3 — FastAPI Backend Endpoints

**Status: Complete**

| Status | Task                                                                 | Notes                                                              |
| ------ | -------------------------------------------------------------------- | ------------------------------------------------------------------ |
| ✅     | Set up FastAPI project with CORS and environment config              |                                                                    |
| ✅     | Auth routes: GitHub OAuth, callback, current user, logout            | JWT-based with Redis blocklist                                     |
| ✅     | Session routes: create, list, get, update, delete                    |                                                                    |
| ✅     | Ingestion routes: status, cancel, freshness check, re-ingest         |                                                                    |
| ✅     | Chat route with SSE streaming                                        |                                                                    |
| ✅     | File routes: list, search, fetch content                             | Content fetched from GitHub API on demand                          |
| ✅     | Share routes: create link, revoke link                               |                                                                    |
| ✅     | Shareable link routes: metadata, chat, history, files                | No auth required                                                   |
| ✅     | Rate limiting on chat endpoints                                      | 30 per day for authenticated users, 20 per day for shared sessions |
| ✅     | Error handling for invalid URLs, large repos, and ingestion failures |                                                                    |
| ✅     | Background task ingestion so the API response returns immediately    | FastAPI BackgroundTasks                                            |

---

## Phase 4 — React Frontend

**Status: Complete**

| Status | Task                                                   | Notes                        |
| ------ | ------------------------------------------------------ | ---------------------------- |
| ✅     | Scaffold Vite + React + TypeScript project             |                              |
| ✅     | GitHub OAuth login and callback handling               | Token stored in localStorage |
| ✅     | Session sidebar with list, create, rename, and delete  |                              |
| ✅     | Repo URL input and session creation flow               |                              |
| ✅     | Ingestion progress page with real-time polling         |                              |
| ✅     | Chat interface with streaming message display          |                              |
| ✅     | Markdown and syntax-highlighted code rendering in chat |                              |
| ✅     | File browser sidebar with tree view                    |                              |
| ✅     | File content modal pulled from GitHub                  |                              |
| ✅     | Shareable link generation and share page               |                              |
| ✅     | Protected routes with auth guard                       |                              |
| ✅     | Responsive layout                                      |                              |
| ✅     | Deploy frontend to Vercel                              |                              |

---

## Phase 5 — AWS Deployment

**Status: Complete**

| Status | Task                                                     | Notes                            |
| ------ | -------------------------------------------------------- | -------------------------------- |
| ✅     | Provision EC2 instance                                   |                                  |
| ✅     | Install Python, dependencies, and configure environment  |                                  |
| ✅     | Set up Nginx as reverse proxy with SSE streaming support | 300s read/send timeouts          |
| ✅     | Configure systemd service for FastAPI                    | Restarts automatically on reboot |
| ✅     | Provision RDS PostgreSQL with pgvector extension         |                                  |
| ✅     | Set up GitHub Actions deploy workflow                    | SSH deploy on push to main       |
| ✅     | SSL via Cloudflare                                       |                                  |
| ✅     | End-to-end testing in production                         |                                  |
| ✅     | Sentry integration for error monitoring                  |                                  |

---

## Phase 6 — Polish and Stretch Goals

**Status: In Progress**

| Status | Task                                             | Notes                |
| ------ | ------------------------------------------------ | -------------------- |
| ✅     | GitHub OAuth for private repo support            | repo scope available |
| ✅     | Repo update detection and re-ingestion           |                      |
| ✅     | Incremental re-ingestion on file changes         |                      |
| ⬜     | Export conversation as Markdown                  | Stretch              |
| ⬜     | Response citations showing which files were used | Stretch              |
| ⬜     | Multi-repo mode                                  | Stretch              |
| 🔵     | README and documentation                         | In progress          |

---

## Development Notes

| Date     | Note                                                                                                                                                                             |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| May 2026 | Replaced LlamaIndex with a custom hybrid search implementation. BM25 runs through PostgreSQL tsvector natively, making the architecture simpler and faster.                      |
| May 2026 | Query expansion added using Claude Haiku before retrieval. Noticeably improves recall on vague or ambiguous questions.                                                           |
| May 2026 | Switched from fixed-size text chunking to Tree-sitter AST-based chunking. Answer quality improved significantly for questions about specific functions or classes.               |
| May 2026 | Ingestion uses a producer-consumer async pattern with 16 concurrent file fetch workers. Processing time for medium-sized repos dropped from several minutes to under 60 seconds. |
