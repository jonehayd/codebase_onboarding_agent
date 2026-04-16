import os

# Set required env vars before any app modules are imported during test collection
os.environ.setdefault("GITHUB_TOKEN", "test")
os.environ.setdefault("OPEN_AI_KEY", "test")
os.environ.setdefault("ANTHROPIC_KEY", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/onboarding_test")
