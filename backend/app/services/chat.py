import logging
from collections.abc import Generator

from sqlalchemy.orm import Session
from sqlalchemy import select, update as sql_update, func

from app.db.models import Messages, Sessions
from app.rag.retriever import retrieve_chunks
from app.rag.prompt_builder import build_prompt
from app.rag.llm_client import stream_responses, get_response
from app.config import MessageRole

logger = logging.getLogger(__name__)

def get_or_create_session(user_id: int, repo_id: int, db: Session) -> Sessions:
    """Get an existing session for the user and repository, or create a new one if it doesn't exist.

    Args:
        user_id (int): The ID of the user.
        repo_id (int): The ID of the repository.
        db (Session): The database session for executing queries.

    Returns:
        Sessions: The existing or newly created session object.
    """
    
    existing = db.execute(
        select(Sessions).where(
            Sessions.user_id == user_id,
            Sessions.repo_id == repo_id,
        )
    ).scalars().first()
    
    if existing:
        return existing
    
    session = Sessions(user_id=user_id, repo_id=repo_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_conversation_history(
    session_id: int,
    db: Session,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Retrieve messages for a session in chronological order with pagination.

    Returns a dict with messages, total count, limit, and offset.
    """
    base = select(Messages).where(Messages.session_id == session_id)

    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar()

    messages = db.execute(
        base.order_by(Messages.created_at.asc()).limit(limit).offset(offset)
    ).scalars().all()

    return {
        "messages": [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages],
        "total": total,
        "limit": limit,
        "offset": offset,
    }

def save_message(session_id: int, role: str, content: str, db: Session) -> Messages:
    """Save a message to the database.

    Args:
        session_id (int): The ID of the session.
        role (str): The role of the message sender ("user" or "assistant").
        content (str): The message content.
        db (Session): The database session.

    Returns:
        Messages: The saved message object.
    """
    
    message = Messages(session_id=session_id, role=role, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def stream_chat(
    user_id: int,
    repo_id: int,
    question: str,
    db: Session,
    top_k: int = 8,
    session_id: int | None = None,
) -> Generator[str, None, None]:
    """Main entry point for the chat pipeline.
    Retrieves relevant chunks, builds a prompt, streams the LLM response,
    and saves the conversation to the database.

    Args:
        user_id (int): The ID of the user.
        repo_id (int): The ID of the repository.
        question (str): The user's question.
        db (Session): The database session.
        top_k (int): Number of chunks to retrieve. Defaults to 8.
        session_id (int | None): Explicit session ID; if None, one is found or created.

    Yields:
        str: Text tokens streamed from the LLM.
    """

    # Use explicit session_id when provided (sessions-centric flow)
    if session_id is not None:
        session = db.get(Sessions, session_id)
    else:
        session = get_or_create_session(user_id, repo_id, db)

    logger.info(
        "Chat request: session=%d repo=%d question_len=%d",
        session.id, repo_id, len(question),
    )

    db.execute(sql_update(Sessions).where(Sessions.id == session.id).values(last_active_at=func.now()))
    db.commit()

    save_message(session.id, MessageRole.USER, question, db)

    chunks = retrieve_chunks(question, repo_id, db, top_k)
    logger.debug("Retrieved %d chunk(s) for session=%d", len(chunks), session.id)

    system, user_message = build_prompt(question, chunks)

    # Stream response and collect full text for saving
    full_response = []

    for token in stream_responses(system, user_message):
        full_response.append(token)
        yield token
        
    # Save assistant response
    save_message(session.id, MessageRole.ASSISTANT, "".join(full_response), db)

def chat(
    user_id: int,
    repo_id: int,
    question: str,
    db: Session,
    top_k: int = 8,
) -> str:
    """Non-streaming version of the chat pipeline. Useful for testing.

    Args:
        user_id (int): The ID of the user.
        repo_id (int): The ID of the repository.
        question (str): The user's question.
        db (Session): The database session.
        top_k (int): Number of chunks to retrieve. Defaults to 8.

    Returns:
        str: The complete response text.
    """
    session = get_or_create_session(user_id, repo_id, db)
    save_message(session.id, MessageRole.USER, question, db)

    chunks = retrieve_chunks(question, repo_id, db, top_k=top_k)
    system, user_message = build_prompt(question, chunks)
    response = get_response(system, user_message)

    save_message(session.id, MessageRole.ASSISTANT, response, db)
    return response


if __name__ == "__main__":
    from sqlalchemy import select
    from app.db.database import init_db, SessionLocal
    from app.db.models import Users, Repositories

    init_db()
    db = SessionLocal()

    try:
        # get first test user and completed repo
        user = db.execute(select(Users)).scalars().first()
        repo = db.execute(
            select(Repositories).where(Repositories.status == "completed")
        ).scalars().first()

        if not user or not repo:
            print("No user or completed repo found. Run analyze.py first.")
        else:
            print(f"Chatting about: {repo.owner}/{repo.name}")
            print(f"As user: {user.username}\n")

            questions = [
                "What does this codebase do?",
                "What are the main functions or classes?",
                "How do I run this project locally?",
            ]

            for question in questions:
                print(f"Q: {question}")
                print("A: ", end="", flush=True)

                for token in stream_chat(user.id, repo.id, question, db):
                    print(token, end="", flush=True)

                print("\n")

    finally:
        db.close()