import os
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from database import db

router = APIRouter()
security = HTTPBearer()

# ── Config ────────────────────────────────────────────────────
GITHUB_CLIENT_ID     = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
JWT_SECRET           = os.getenv("JWT_SECRET", "owlint-secret-change-in-prod")
JWT_ALGORITHM        = "HS256"
JWT_EXPIRE_HOURS     = 24 * 7   # 1 week
FRONTEND_URL         = os.getenv("FRONTEND_URL", "http://localhost:3000")


# ── JWT helpers ───────────────────────────────────────────────

def create_token(user_id: str, github_username: str) -> str:
    payload = {
        "sub": user_id,
        "username": github_username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"github_id": user_id})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return await decode_token(credentials.credentials)


# ── GitHub OAuth Routes ───────────────────────────────────────

@router.get("/auth/github/login")
async def github_login():
    """Redirect user to GitHub OAuth page."""
    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&scope=read:user,user:email"
    )
    return RedirectResponse(github_url)


@router.get("/auth/github/callback")
async def github_callback(code: str):
    """
    GitHub redirects here with a code.
    Exchange code → access token → user info → JWT → redirect to frontend.
    """
    # 1. Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
        )
    token_data = token_res.json()
    access_token = token_data.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub OAuth failed")

    # 2. Fetch GitHub user info
    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    github_user = user_res.json()

    github_id       = str(github_user["id"])
    github_username = github_user["login"]
    avatar_url      = github_user.get("avatar_url", "")
    email           = github_user.get("email", "")

    # 3. Upsert user in MongoDB
    await db.users.update_one(
        {"github_id": github_id},
        {"$set": {
            "github_id": github_id,
            "username": github_username,
            "avatar_url": avatar_url,
            "email": email,
            "last_login": datetime.utcnow(),
        },
         "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True,
    )

    # 4. Create JWT
    jwt_token = create_token(github_id, github_username)

    # 5. Redirect to frontend with token
    return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={jwt_token}")


@router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return current logged-in user info."""
    return {
        "github_id":  current_user["github_id"],
        "username":   current_user["username"],
        "avatar_url": current_user.get("avatar_url", ""),
        "email":      current_user.get("email", ""),
    }


@router.post("/auth/logout")
async def logout():
    """Frontend just deletes the token. This endpoint is a no-op but good practice."""
    return {"message": "Logged out successfully"}
