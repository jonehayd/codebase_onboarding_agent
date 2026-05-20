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
    """Retrieve chunks using hybrid BM25 + semantic search with Reciprocal Rank Fusion.

    Both arms independently rank up to `candidate_k` chunks. RRF merges the two
    ranked lists: score = 1/(60+semantic_rank) + 1/(60+keyword_rank). Chunks that
    appear in only one arm receive a penalty rank of candidate_k+1 for the missing arm.

    Returns top_k results ordered by RRF score (best first). Each result carries
    `distance` (raw cosine distance from the semantic arm, or 2.0 for keyword-only
    matches) so downstream dedup logic in retrieve_chunks_multi_query stays unchanged.
    """
    query_vector = embed_query(query)
    candidate_k = max(top_k * 10, 60)

    stmt = text("""
        WITH semantic AS (
            SELECT
                cc.id,
                cc.embedding <=> CAST(:query_vector AS vector) AS sem_distance,
                ROW_NUMBER() OVER (
                    ORDER BY cc.embedding <=> CAST(:query_vector AS vector)
                ) AS rank
            FROM code_chunks cc
            JOIN files f ON f.id = cc.file_id
            WHERE f.repo_id = :repo_id
              AND cc.embedding IS NOT NULL
            ORDER BY cc.embedding <=> CAST(:query_vector AS vector)
            LIMIT :candidate_k
        ),
        keyword AS (
            SELECT
                cc.id,
                ROW_NUMBER() OVER (
                    ORDER BY ts_rank(cc.content_tsv,
                                     websearch_to_tsquery('english', :query_text)) DESC
                ) AS rank
            FROM code_chunks cc
            JOIN files f ON f.id = cc.file_id
            WHERE f.repo_id = :repo_id
              AND cc.content_tsv @@ websearch_to_tsquery('english', :query_text)
            ORDER BY ts_rank(cc.content_tsv,
                             websearch_to_tsquery('english', :query_text)) DESC
            LIMIT :candidate_k
        ),
        combined AS (
            SELECT
                COALESCE(s.id, k.id) AS id,
                s.sem_distance,
                (1.0 / (60 + COALESCE(s.rank, :candidate_k + 1)) +
                 1.0 / (60 + COALESCE(k.rank, :candidate_k + 1))) AS rrf_score
            FROM semantic s
            FULL OUTER JOIN keyword k ON s.id = k.id
        )
        SELECT
            cc.id, cc.chunk_type, cc.name, cc.content,
            cc.start_line, cc.end_line, f.file_path,
            COALESCE(c.sem_distance, 2.0) AS distance,
            c.rrf_score
        FROM combined c
        JOIN code_chunks cc ON cc.id = c.id
        JOIN files f ON f.id = cc.file_id
        ORDER BY c.rrf_score DESC
        LIMIT :top_k
    """)

    rows = db.execute(stmt, {
        "query_vector": str(query_vector),
        "query_text": query,
        "repo_id": repo_id,
        "top_k": top_k,
        "candidate_k": candidate_k,
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
            "rrf_score": row.rrf_score,
        }
        for row in rows
    ]


def retrieve_chunks_multi_query(
    question: str, repo_id: int, db: Session, top_k: int = 15
) -> list[dict]:
    """Retrieve chunks using the original question plus LLM-generated sub-queries.

    Each sub-query is embedded and searched independently. Results are merged by
    chunk ID, keeping the lowest (best) distance seen across all queries, then
    sorted by distance ascending.
    """
    from app.rag.llm_client import expand_query

    queries = expand_query(question)
    best: dict[int, dict] = {}

    for query in queries:
        for chunk in retrieve_chunks(query, repo_id, db, top_k=top_k):
            chunk_id = chunk["id"]
            if chunk_id not in best or chunk["rrf_score"] > best[chunk_id]["rrf_score"]:
                best[chunk_id] = chunk

    return sorted(best.values(), key=lambda c: c["rrf_score"], reverse=True)


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