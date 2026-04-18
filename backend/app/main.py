from fastapi import FastAPI
from app.api.routes.auth import router as auth_router
from app.db.database import init_db

app = FastAPI()

app.include_router(auth_router)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
async def root():
    return {"message": "Welcome to the Codebase Onboarding Agent API!"}

