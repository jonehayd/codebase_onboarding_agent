from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Application configuration using Pydantic ---

class Settings(BaseSettings):
    # Environment variables
    github_token: str | None = None
    open_ai_key: str
    anthropic_key: str
    database_url: str
    
    # JWT & OAuth settings
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    github_client_id: str
    github_client_secret: str
    
    frontend_url: str = "http://localhost:5173"
    redis_url: str | None = None

    # Session settings
    max_sessions_per_user: int = 5
    max_characters_per_question: int = 1000
    max_characters_per_title: int = 100

    # Repository processing settings
    max_file_size_bytes: int = 100_000 # Skip files larger than 100 KB
    max_files_per_repo: int = 2_000    # Stop fetching after this many files
    max_repo_size_kb: int = 500_000    # Reject repos larger than ~500 MB (GitHub reports in KB)
    
    # Embedding settings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    top_k_chunks: int = 5
    
    # LLM settings
    anthropic_model: str = "claude-haiku-4-5"
    query_expansion_model: str = "claude-haiku-4-5-20251001"
    max_response_tokens: int = 1024
    temperature: float = 0.7

    model_config = SettingsConfigDict(env_file=".env")
    
settings = Settings()

# --- Enums for consistent status and role values ---

class RepoStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    
class ChunkType(StrEnum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    IMPORT = "import"
    OTHER = "other"

class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"