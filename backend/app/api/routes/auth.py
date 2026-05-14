import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import get_current_user
from app.api.schemas import UserOut
from app.config import settings
from app.db.database import get_db
from app.db.models import Users
from app.utility.auth import add_to_blocklist, create_token

_bearer = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAIL_URL = "https://api.github.com/user/emails"

@router.get("/github")
def github_login(private: bool = False):
    """Redirects the user to GitHub's OAuth authorization page.

    Args:
        private: If True, requests repo scope for private repository access.
    """
    scope = "read:user user:email repo" if private else "read:user user:email"
    params = {
        "client_id": settings.github_client_id,
        "scope": scope,
        "state": "repo" if private else "basic",
    }
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"{GITHUB_AUTH_URL}?{query_string}")

@router.get("/github/callback")
@limiter.limit("20/hour")
def github_callback(request: Request,code: str, state: str | None = None, db: Session = Depends(get_db)):
    """Handles the callback from GitHub after user authorization.

    Args:
        code (str): The authorization code returned by GitHub.
        state (str | None): The state parameter to determine if repo access was requested.
        db (Session): The database session.
    
    Returns:
        dict: A JSON response containing the JWT token and user info.
    """
    
    github_token = _exchange_code_for_token(code)
    profile = _fetch_github_profile(github_token)
    email = _fetch_github_email(github_token)
    
    github_id = str(profile["id"])
    username = profile["login"]
    has_repo_access = (state == "repo")
    
    # upsert user - create if new, update token if existing
    user = db.execute(select(Users).where(Users.github_id == github_id)).scalar_one_or_none()
    
    if user is None:
        user = Users(
            github_id=github_id,
            username=username,
            email=email,
            github_token=github_token,
            has_repo_access=has_repo_access,
        )
        db.add(user)
    else:
        user.github_token = github_token
        user.username = username
        user.has_repo_access = has_repo_access
        if email:
            user.email = email
    db.commit()
    db.refresh(user)

    jwt_token = create_token(user.id)

    redirect_url = f"{settings.frontend_url}/auth/callback?token={jwt_token}"
    return RedirectResponse(url=redirect_url, status_code=302)
    
@router.get("/me", response_model=UserOut)
def get_me(current_user: Users = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "has_repo_access": current_user.has_repo_access,
        "created_at": current_user.created_at,
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    current_user: Users = Depends(get_current_user),
):
    """Revoke the current JWT so it cannot be used again."""
    add_to_blocklist(credentials.credentials)


def _exchange_code_for_token(code: str) -> str:
    """Exchange a GitHub OAuth code for an access token.

    Args:
        code (str): The authorization code from GitHub.

    Returns:
        str: The GitHub access token.

    Raises:
        HTTPException: If the token exchange fails.
    """
    response = httpx.post(
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
        },
    )

    data = response.json()

    if "error" in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub OAuth error: {data.get('error_description', data['error'])}",
        )

    return data["access_token"]


def _fetch_github_profile(token: str) -> dict:
    """Fetch the authenticated user's GitHub profile.

    Args:
        token (str): The GitHub access token.

    Returns:
        dict: The user's GitHub profile.

    Raises:
        HTTPException: If the profile fetch fails.
    """
    response = httpx.get(
        GITHUB_USER_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch GitHub profile",
        )

    return response.json()


def _fetch_github_email(token: str) -> str | None:
    """Fetch the authenticated user's primary verified email from GitHub.
    Needed because users can set their email to private on their profile.

    Args:
        token (str): The GitHub access token.

    Returns:
        str | None: The primary verified email, or None if not found.
    """
    response = httpx.get(
        GITHUB_EMAIL_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )

    if response.status_code != 200:
        return None

    emails = response.json()
    for entry in emails:
        if entry.get("primary") and entry.get("verified"):
            return entry["email"]

    return None
        
    