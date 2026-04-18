from datetime import datetime, timedelta, timezone
from jose import jwt
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