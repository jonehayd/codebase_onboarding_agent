# Codebase Onboarding Assistant
**Project Plan** | Hayden Jones | Last updated: April 2026

---

## Status Key

| Symbol | Meaning |
|---|---|
| ⬜ | Not Started |
| 🔵 | In Progress |
| ✅ | Done |
| 🔴 | Blocked |

---

## Timeline Summary

| Phase | Description | Estimated Time | Status |
|---|---|---|---|
| 1 | Repo Ingestion Pipeline | 2–3 weeks | ⬜ Not Started |
| 2 | Query & Retrieval (RAG) | 1–2 weeks | ⬜ Not Started |
| 3 | FastAPI Backend Endpoints | 3–5 days | ⬜ Not Started |
| 4 | React Frontend | 1 week | ⬜ Not Started |
| 5 | AWS Deployment | 3–5 days | ⬜ Not Started |
| 6 | Polish & Stretch Goals | 1 week+ | ⬜ Not Started |
| | **Total (part time)** | **6–10 weeks** | |

---

## Phase 1 — Repo Ingestion Pipeline
**Estimated time:** 2–3 weeks | The most important phase. Get this right before anything else.

| Status | Task | Notes |
|---|---|---|
| ⬜ | Set up Python project structure and virtual environment | |
| ⬜ | Install and configure PyGithub for GitHub API access | |
| ⬜ | Implement repo fetching — file tree traversal, filtering binaries and lock files | |
| ⬜ | Install Tree-sitter and language grammars (Python, TS, JS, Java, Go) | |
| ⬜ | Build AST parser to extract functions, classes, routes, and imports per file | |
| ⬜ | Design chunking strategy based on code structure, not fixed char counts | Critical — spend the most time here |
| ⬜ | Set up PostgreSQL locally with pgvector extension | |
| ⬜ | Design database schema: repos, files, chunks, embeddings tables | |
| ⬜ | Implement embedding generation (OpenAI or sentence-transformers) | |
| ⬜ | Store chunks and embeddings in pgvector | |
| ⬜ | Implement commit hash caching — skip re-ingestion if repo unchanged | |
| ⬜ | Set up AWS S3 bucket and implement raw file caching | |
| ⬜ | Write unit tests for parser and chunking logic | |
| ⬜ | Test ingestion end-to-end on 3–4 real repos of varying sizes | |

---

## Phase 2 — Query & Retrieval (RAG)
**Estimated time:** 1–2 weeks | Tune retrieval quality before building the API layer.

| Status | Task | Notes |
|---|---|---|
| ⬜ | Set up LlamaIndex and configure pgvector as the vector store | |
| ⬜ | Implement query embedding pipeline | |
| ⬜ | Build similarity search against pgvector with configurable top-k | |
| ⬜ | Design prompt template — how chunks + question are assembled for the LLM | |
| ⬜ | Integrate Anthropic or OpenAI API for completions | |
| ⬜ | Implement streaming response support | |
| ⬜ | Maintain conversation history per session for follow-up questions | |
| ⬜ | Test retrieval quality across different question types | Ask about endpoints, auth, setup, deps |
| ⬜ | Tune chunk size and top-k until answer quality is acceptable | Iterate here |

---

## Phase 3 — FastAPI Backend Endpoints
**Estimated time:** 3–5 days | Straightforward once phases 1 and 2 are solid.

| Status | Task | Notes |
|---|---|---|
| ⬜ | Set up FastAPI project with CORS and environment config | |
| ⬜ | POST /analyze — accepts GitHub URL, kicks off ingestion job | |
| ⬜ | GET /status/{repo_id} — returns ingestion progress | |
| ⬜ | POST /chat — accepts question + session, returns streamed answer | |
| ⬜ | GET /repo/{repo_id} — returns repo metadata and file tree | |
| ⬜ | Add rate limiting to prevent API cost blowout | |
| ⬜ | Add error handling for invalid URLs, private repos, large repos | |
| ⬜ | Write API integration tests | |

---

## Phase 4 — React Frontend
**Estimated time:** 1 week | Should be the fastest phase given existing React experience.

| Status | Task | Notes |
|---|---|---|
| ⬜ | Scaffold Vite + React + TypeScript project | |
| ⬜ | Build repo URL input with validation and submit handler | |
| ⬜ | Build ingestion progress indicator — polling /status endpoint | |
| ⬜ | Build chat interface with message history and streaming display | |
| ⬜ | Handle streamed responses from backend | |
| ⬜ | Add shareable link generation for processed repos | |
| ⬜ | Add file tree sidebar showing indexed files | |
| ⬜ | Error states — invalid repo, ingestion failure, API errors | |
| ⬜ | Basic responsive styling | |
| ⬜ | Deploy frontend to Vercel | |

---

## Phase 5 — AWS Deployment
**Estimated time:** 3–5 days | Expect this to take longer than it looks the first time.

| Status | Task | Notes |
|---|---|---|
| ⬜ | Provision EC2 instance (t3.small or t3.medium) | |
| ⬜ | Install Python, dependencies, and configure environment variables | |
| ⬜ | Set up nginx as reverse proxy in front of gunicorn/uvicorn | |
| ⬜ | Configure systemd service so FastAPI restarts on reboot | |
| ⬜ | Provision RDS PostgreSQL instance and enable pgvector extension | |
| ⬜ | Create S3 bucket and configure IAM permissions | |
| ⬜ | Point onboard.hjones.dev at EC2 via Cloudflare or Route 53 | |
| ⬜ | Set up SSL certificate (Let's Encrypt or Cloudflare) | |
| ⬜ | Test full end-to-end flow on production environment | |
| ⬜ | Set up CloudWatch or basic logging for error monitoring | |

---

## Phase 6 — Polish & Stretch Goals
**Estimated time:** 1 week+ | Nice-to-haves after MVP is live.

| Status | Task | Notes |
|---|---|---|
| ⬜ | Add GitHub OAuth for private repo support | Stretch |
| ⬜ | Export conversation as Markdown | Stretch |
| ⬜ | Repo update detection — re-index on new commits | Stretch |
| ⬜ | Multi-language support beyond the initial 5 | Stretch |
| ⬜ | Add response citations — which files were used to answer | Stretch |
| ⬜ | Write a good README with demo video | Required for resume |
| ⬜ | Pin repo on GitHub profile | |
| ⬜ | Add project to resume and portfolio site | |

---

## Development Notes

| Date | Note |
|---|---|
| | |
| | |
| | |
| | |
| | |
| | |
| | |
| | |
