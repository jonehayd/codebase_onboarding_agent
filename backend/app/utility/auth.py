import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.config import settings


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def add_to_blocklist(token: str, db: Session) -> None:
    from app.db.models import RevokedTokens
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    except JWTError:
        return
    entry = RevokedTokens(token_hash=_hash_token(token), expires_at=expires_at)
    db.add(entry)
    db.commit()


def is_blocklisted(token: str, db: Session) -> bool:
    from app.db.models import RevokedTokens
    token_hash = _hash_token(token)
    result = db.execute(
        select(RevokedTokens).where(RevokedTokens.token_hash == token_hash)
    ).scalar_one_or_none()
    return result is not None


def purge_expired_revoked_tokens(db: Session) -> int:
    from app.db.models import RevokedTokens
    result = db.execute(
        delete(RevokedTokens).where(RevokedTokens.expires_at < datetime.now(timezone.utc))
    )
    db.commit()
    return result.rowcount


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
