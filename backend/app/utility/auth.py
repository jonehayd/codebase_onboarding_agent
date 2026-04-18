from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from jose import JWTError, jwt
from app.config import settings

def create_token(user_id: int) -> str:
    """Create a JWT token for the authenticated user.

    Args:
        user_id (int): The ID of the authenticated user.

    Returns:
        str: The JWT token.
    """
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> int:
    """Decode a JWT token and return the user ID.

    Args:
        token (str): The JWT token string.

    Raises:
        HTTPException: If the token is invalid or expired.

    Returns:
        int: The user ID extracted from the token.
    """
    
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )