import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

# Make sure `app` is importable when running from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import Base
import app.db.models  # noqa: F401 — registers all models with Base metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    from app.config import settings
    return settings.database_url


def _render_item(type_: str, obj, autogen_context) -> str | bool:
    """Teach autogenerate how to render pgvector's Vector type."""
    if type_ == "type":
        try:
            from pgvector.sqlalchemy import Vector
            if isinstance(obj, Vector):
                autogen_context.imports.add("from pgvector.sqlalchemy import Vector")
                return f"Vector({obj.dim})"
        except ImportError:
            pass
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=_render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=_render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
