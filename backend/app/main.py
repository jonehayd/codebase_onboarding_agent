import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.share import router as share_router
from app.db.database import init_db, SessionLocal
from app.services.sessions import purge_stale_sessions

# Identify and rate limit a client by IP address
limiter = Limiter(key_func=get_remote_address)

async def _session_cleanup_loop():
    while True:
        db = SessionLocal()
        try:
            await asyncio.to_thread(purge_stale_sessions, db)
        finally:
            db.close()
        await asyncio.sleep(24 * 60 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    cleanup_task = asyncio.create_task(_session_cleanup_loop())
    yield
    cleanup_task.cancel()
    
app = FastAPI(
    title="Codebase Onboarding Agent",
    description="Ask questions about any GitHub repository",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(share_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Welcome to the Codebase Onboarding Agent API!"}

