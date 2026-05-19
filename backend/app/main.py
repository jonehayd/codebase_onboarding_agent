import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.auth import router as auth_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.share import router as share_router
from app.config import settings
from app.core.limiter import limiter
from app.core.logging import setup_logging
from app.core.errors import (
    http_exception_handler,
    rate_limit_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.db.database import init_db, SessionLocal
from app.services.sessions import purge_stale_sessions

setup_logging()
logger = logging.getLogger(__name__)

async def _session_cleanup_loop():
    while True:
        db = SessionLocal()
        try:
            count = await asyncio.to_thread(purge_stale_sessions, db)
            if count:
                logger.info("Session cleanup: purged %d stale session(s)", count)
        finally:
            db.close()
        await asyncio.sleep(24 * 60 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Codebase Onboarding Agent")
    init_db()
    cleanup_task = asyncio.create_task(_session_cleanup_loop())
    yield
    cleanup_task.cancel()
    logger.info("Shutting down")

app = FastAPI(
    title="Codebase Onboarding Agent",
    description="Ask questions about any GitHub repository",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
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

