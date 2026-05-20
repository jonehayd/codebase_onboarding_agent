# Codebase Onboarding Agent

![React](https://img.shields.io/badge/React_19-20232A?style=flat-square&logo=react&logoColor=61DAFB)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL_16-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Claude](https://img.shields.io/badge/Claude_AI-D4A574?style=flat-square&logo=anthropic&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI_Embeddings-412991?style=flat-square&logo=openai&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?style=flat-square&logo=amazonwebservices&logoColor=white)

**[Try it live](https://codebaseonboardingagent.hjones.dev/)**

Paste a GitHub repository URL, wait while the code gets indexed, and then ask questions about it in plain English.

This is useful when you're inheriting someone else's code, evaluating an open source project before adopting it, or trying to help a teammate understand a codebase they've never seen. No IDE plugin needed, no local clone required, just a URL.

---

## How It Works

When you submit a repo URL, the backend fetches all the source files from GitHub and parses them with Tree-sitter. Tree-sitter is a code parsing library that understands the actual structure of code rather than treating it as plain text. It extracts individual functions, classes, and imports for each file and breaks them into chunks that are meaningful on their own.

Each chunk is converted into a vector embedding using OpenAI's embedding model and stored in PostgreSQL alongside a full-text search index. When you ask a question, the app searches using both keyword matching and semantic similarity at the same time, then combines the results with a ranking algorithm called Reciprocal Rank Fusion to surface the most relevant code.

Before that search runs, your question goes through an expansion step. Claude generates a few variations of your question to improve the chances of finding relevant code, even when your wording doesn't exactly match how something was written in the codebase. The retrieved chunks get assembled into a prompt, and the response streams back to you in real time.

Chat history is saved per session, so you can ask follow-up questions and the context carries forward naturally.

---

## Features

- **GitHub OAuth login** so you can save and revisit your sessions
- **Ingestion progress tracking** so you can see what's happening while a repo is being indexed
- **Streaming chat responses** that appear in real time as Claude generates them
- **Hybrid search** combining semantic similarity and keyword matching for more reliable retrieval
- **Persistent session history** so you can pick up a conversation where you left off
- **File browser** to view the actual source files alongside the chat
- **Shareable links** that give anyone read-only access to a processed repo without an account
- **Re-ingestion support** when a repo has been updated since it was last indexed
- **Rate limiting** to keep API costs reasonable
- Code parsing support for Python, TypeScript, JavaScript, Java, and Go

---

## Tech Stack

### Frontend

The frontend is built with **React 19** and **Javascript**, bundled with **Vite**. Styling uses **TailwindCSS**. **TanStack Query** manages server state and handles caching on the client side. Chat responses stream from the backend via Server-Sent Events and are rendered with markdown and syntax-highlighted code blocks.

### Backend

The API is a **FastAPI** application running on Python 3.12. FastAPI handles async operations naturally, which matters during ingestion when the backend is fetching files and generating embeddings concurrently. **SQLAlchemy** is the ORM and **Alembic** handles database migrations.

### Database

**PostgreSQL 16** is the main database. The **pgvector** extension adds support for storing and querying vector embeddings directly in Postgres, which keeps the stack simple by eliminating the need for a separate vector database. Full-text search runs through PostgreSQL's native `tsvector` columns, which is what makes the hybrid search possible without any additional search infrastructure.

**Redis** is used as a lightweight in-memory store for tracking ingestion progress and cancellation state between requests.

### AI and Embeddings

Embeddings are generated with **OpenAI's text-embedding-3-small** model. This converts code chunks and user questions into numerical vectors so they can be compared by how semantically similar they are to each other.

Chat responses come from **Anthropic's Claude** (claude-haiku-4-5). Claude also handles query expansion before each retrieval step, rewriting the user's question a few different ways to improve the chance of finding relevant results.

### Code Parsing

**Tree-sitter** is what allows the ingestion pipeline to understand code structure rather than just read raw text. It builds an abstract syntax tree for each file and walks it to extract functions, classes, imports, and methods as individual chunks. This produces context that is semantically coherent, rather than code cut off at arbitrary character counts.

### Infrastructure

The backend runs on **AWS EC2** behind an **Nginx** reverse proxy, managed as a systemd service. The frontend is deployed on **Vercel**. Everything is containerized with **Docker** and **Docker Compose** for local development.

---

## Running Locally

**Prerequisites:** Docker, Python 3.12+, Node 18+

```bash
# Clone the repo
git clone https://github.com/jonehayd/codebase_onboarding_agent.git
cd codebase_onboarding_agent

# Start Postgres and Redis
docker compose up db redis -d

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys and config in .env
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

The app will be running at `http://localhost:5173`.

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in the following required values:

| Variable               | Description                                                 |
| ---------------------- | ----------------------------------------------------------- |
| `ANTHROPIC_KEY`        | Anthropic API key for chat responses                        |
| `OPEN_AI_KEY`          | OpenAI API key for generating embeddings                    |
| `GITHUB_CLIENT_ID`     | GitHub OAuth app client ID                                  |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth app client secret                              |
| `DATABASE_URL`         | PostgreSQL connection string                                |
| `JWT_SECRET`           | Random secret string used to sign auth tokens               |
| `REDIS_URL`            | Redis connection string (default: `redis://localhost:6379`) |
| `FRONTEND_URL`         | Frontend origin for CORS (default: `http://localhost:5173`) |

See `.env.example` for the full list including optional tuning parameters.
