# Codebase Onboarding Assistant
**Project Overview** | Hayden Jones | hjones.dev | github.com/jonehayd

---

## What It Is

A web application that lets developers, team leads, and new hires understand an unfamiliar codebase by asking questions about it in plain English. A user pastes a public GitHub repository URL, the system ingests and indexes the codebase, and they can then ask questions like:

- What are the API endpoints and what do they do?
- How does authentication work in this project?
- What would I need to change to add a new database model?
- How do I run this project locally?
- What third-party services does this project depend on?

The goal is not to generate static documentation. It is to give developers an interactive way to build a mental model of a codebase quickly, without having to read every file manually.

---

## Problem Being Solved

Every developer has experienced the pain of joining a project mid-stream or inheriting someone else's code. Existing tools either require an IDE plugin installed locally, generate static documentation that goes stale, or require the full codebase to fit in a context window. There is no standalone web tool that lets you paste a GitHub URL and immediately start asking intelligent questions about the code.

This tool is aimed at:

- New developers onboarding to an unfamiliar codebase
- Team leads sharing codebase context with non-technical stakeholders
- Developers auditing or reviewing an open source project before using it
- Freelancers or contractors getting up to speed on a client codebase quickly

---

## Tech Stack

| Layer | Tools & Libraries |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI |
| LLM | Anthropic API (Claude) or OpenAI API |
| Code Parsing | Tree-sitter (AST parsing across multiple languages) |
| RAG Pipeline | LlamaIndex — chunking, embedding, retrieval |
| Embeddings | OpenAI text-embedding-3-small or sentence-transformers |
| Database | PostgreSQL + pgvector extension |
| Repo Ingestion | GitHub REST API via PyGithub |
| File Storage | AWS S3 (raw repo snapshots) |
| Hosting | AWS EC2 (backend), AWS RDS (database), Vercel (frontend) |
| Domain | onboard.hjones.dev |

---

## System Architecture

### Repo Ingestion Pipeline

When a user submits a GitHub URL, the backend fetches the repository contents via the GitHub API. Files are filtered to exclude binaries, lock files, and build artifacts. Each code file is parsed with Tree-sitter to extract structured information — functions, classes, route definitions, imports, and docstrings. The parsed content is chunked intelligently based on code structure rather than fixed character counts, embedded using an embedding model, and stored in PostgreSQL with pgvector. Raw file contents are cached in S3 so the same repo is not re-fetched on repeat visits.

### Query & Retrieval Pipeline

When a user asks a question, it is embedded using the same embedding model. A similarity search against pgvector retrieves the most relevant code chunks. These chunks are assembled into a structured prompt alongside the user question and sent to the LLM API. The response is streamed back to the frontend and displayed in the chat interface. Conversation history is maintained in the session so follow-up questions have context.

### Caching Strategy

Processed repos are stored in the database with a hash of their latest commit. If a user submits a URL that has already been ingested and the commit hash has not changed, the system skips re-processing and loads the existing embeddings. This keeps repeat queries fast and avoids unnecessary API and compute costs.

---

## Features

### Core (MVP)

- GitHub URL input with repo validation and ingestion progress indicator
- Conversational chat interface with streaming responses
- Multi-language support via Tree-sitter grammars (Python, TypeScript, JavaScript, Java, Go)
- Repo caching — same repo does not get re-processed on repeat visits
- Shareable link to a processed repo so teammates can use the same session

### Stretch Goals

- Private repo support via GitHub OAuth
- Export conversation as Markdown or PDF
- Repo update detection — re-indexes when the main branch has new commits
- Multi-repo mode — ask questions across multiple related repos at once
- Confidence indicators on responses that cite which files were used

---

## What Makes It Different

GitHub Copilot and similar tools require an IDE and a locally cloned repo. This tool is a standalone web app — nothing to install, works from a URL, and is shareable. The target user is not necessarily someone writing code right now; it is anyone who needs to understand a codebase from the outside. The Tree-sitter AST parsing layer means the system understands code structure rather than treating source files as raw text, which leads to more precise context retrieval and better answers.
