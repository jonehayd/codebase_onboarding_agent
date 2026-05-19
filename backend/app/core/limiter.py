from fastapi import Request
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


def _get_rate_limit_key(request: Request) -> str:
    """Key authenticated requests by user ID, unauthenticated by IP.

    This prevents shared-IP collisions (offices, VPNs) while still
    protecting unauthenticated endpoints like the OAuth login flow.
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except JWTError:
            pass
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_rate_limit_key,
    storage_uri=settings.redis_url,
)
