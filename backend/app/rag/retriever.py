import re

from requests import Session
from sqlalchemy import select, text

from app.db.models import Files
from app.rag.embeddings import embed_query

PINNED_FILENAMES = {
    "package.json", "requirements.txt", "go.mod", "Cargo.toml", "pyproject.toml",
    "docker-compose.yml", "docker-compose.yaml", "Dockerfile", "README.md",
}

_PINNED_PATTERN = "(" + "|".join(re.escape(n) for n in PINNED_FILENAMES) + ")$"


def list_repo_files(repo_id: int, db: Session) -> list[str]:
    """Return all file paths ingested for a repository, sorted alphabetically."""
    rows = db.execute(
        select(Files.file_path)
        .where(Files.repo_id == repo_id)
        .order_by(Files.file_path)
    ).scalars().all()
    return list(rows)


def get_pinned_chunks(repo_id: int, db: Session) -> list[dict]:
    """Return chunks from always-included config/dependency files for a repository.

    These files (package.json, requirements.txt, docker-compose.yml, etc.) are injected
    into every prompt regardless of query similarity so that dependency/stack questions
    are always answered from ground truth rather than inferred from code samples.
    """
    rows = db.execute(
        text("""
            SELECT cc.id, cc.chunk_type, cc.name, cc.content,
                   cc.start_line, cc.end_line, f.file_path, 0.0 AS distance
            FROM code_chunks cc
            JOIN files f ON f.id = cc.file_id
            WHERE f.repo_id = :repo_id
              AND f.file_path ~ :pattern
            ORDER BY f.file_path, cc.start_line
        """),
        {"repo_id": repo_id, "pattern": _PINNED_PATTERN},
    ).fetchall()
    return [{**dict(row._mapping), "pinned": True} for row in rows]


def retrieve_chunks(query: str, repo_id: int, db: Session, top_k: int = 15) -> list[dict]:
    """
    Retrieve relevant chunks from the database based on the query and repository ID.
    
    Args:
        query (str): The input query for which relevant chunks are to be retrieved.
        repo_id (int): The ID of the repository to filter the chunks.
        db (Session): The database session for executing queries.
        top_k (int): The number of top relevant chunks to retrieve (default is 8).
    
    Returns:
        list[dict]: A list of dictionaries containing the retrieved chunks and their metadata.
    """
    
    query_vector = embed_query(query)
    
    stmt = text("""
                SELECT cc.id,
                cc.chunk_type,
                cc.name,
                cc.content,
                cc.start_line,
                cc.end_line,
                f.file_path,
                cc.embedding <=> CAST(:query_vector AS vector) AS distance
                FROM code_chunks cc
                JOIN files f ON f.id = cc.file_id
                WHERE f.repo_id = :repo_id
                    AND cc.embedding IS NOT NULL
                ORDER BY distance ASC
                LIMIT :top_k
            """)
    
    rows = db.execute(stmt, {
        "query_vector": str(query_vector),
        "repo_id": repo_id,
        "top_k": top_k,
    }).fetchall()
    
    return [
        {
            "id": row.id,
            "chunk_type": row.chunk_type,
            "name": row.name,
            "content": row.content,
            "start_line": row.start_line,
            "end_line": row.end_line,
            "file_path": row.file_path,
            "distance": row.distance,
        }
        for row in rows
    ]
    

# --- manual test code ---
if __name__ == "__main__":
    from app.db.database import init_db, SessionLocal
    from app.db.models import Repositories

    init_db()
    db = SessionLocal()

    try:
        repo = db.execute(
            select(Repositories).where(Repositories.status == "completed")
        ).scalars().first()

        if not repo:
            print("No completed repos found. Run analyze.py first.")
        else:
            print(f"Searching repo: {repo.owner}/{repo.name}\n")

            test_queries = [
                "how does authentication work?",
                "what are the API endpoints?",
                "how is the database connected?",
            ]

            for query in test_queries:
                print(f"Query: {query}")
                chunks = retrieve_chunks(query, repo.id, db, top_k=3)
                for chunk in chunks:
                    print(f"  [{chunk['chunk_type']}] {chunk['name']} — {chunk['file_path']} lines {chunk['start_line']}-{chunk['end_line']} (distance: {chunk['distance']:.4f})")
                print()

    finally:
        db.close()