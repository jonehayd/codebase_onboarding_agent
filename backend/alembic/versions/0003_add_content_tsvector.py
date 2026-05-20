"""add content_tsv generated column to code_chunks

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-19

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Generated column — maintained automatically by Postgres whenever content changes.
    # op.add_column cannot express GENERATED ALWAYS AS, so we use raw DDL.
    op.execute("""
        ALTER TABLE code_chunks
        ADD COLUMN content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
    """)
    op.execute("""
        CREATE INDEX ix_code_chunks_content_tsv
        ON code_chunks USING GIN(content_tsv)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_code_chunks_content_tsv")
    op.execute("ALTER TABLE code_chunks DROP COLUMN IF EXISTS content_tsv")
