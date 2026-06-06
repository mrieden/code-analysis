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
        f"&scope=read:user,user:email,repo"
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
            "github_access_token": access_token,
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


# ── GitHub repo browsing (logged-in users) ────────────────
GITHUB_API = "https://api.github.com"


async def _github_get(token: str, url: str, params=None):
    """Authenticated GET against the GitHub REST API."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            params=params,
        )
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail=f"GitHub API error: {res.text}")
    return res.json()


def _require_github_token(current_user: dict) -> str:
    token = current_user.get("github_access_token")
    if not token:
        raise HTTPException(status_code=400, detail="No GitHub access token. Please sign in again.")
    return token


@router.get("/github/repos")
async def github_repos(current_user: dict = Depends(get_current_user)):
    """List the logged-in user's repositories."""
    token = _require_github_token(current_user)

    repos, page = [], 1
    while True:
        data = await _github_get(
            token,
            f"{GITHUB_API}/user/repos",
            params={
                "per_page": 100,
                "page": page,
                "sort": "updated",
                "affiliation": "owner,collaborator,organization_member",
            },
        )
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1

    return [
        {
            "name": r["name"],
            "full_name": r["full_name"],
            "owner": r["owner"]["login"],
            "private": r["private"],
            "default_branch": r.get("default_branch", "main"),
        }
        for r in repos
    ]


@router.get("/github/tree")
async def github_tree(owner: str, repo: str, branch: str = None,
                      current_user: dict = Depends(get_current_user)):
    """List all files (blobs) in a repository."""
    token = _require_github_token(current_user)

    if not branch:
        repo_info = await _github_get(token, f"{GITHUB_API}/repos/{owner}/{repo}")
        branch = repo_info.get("default_branch", "main")

    tree = await _github_get(
        token,
        f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}",
        params={"recursive": "1"},
    )
    files = [
        {"path": t["path"], "type": t["type"]}
        for t in tree.get("tree", [])
        if t.get("type") == "blob"
    ]
    return {"branch": branch, "files": files}


@router.get("/github/file")
async def github_file(owner: str, repo: str, path: str, branch: str = None,
                      current_user: dict = Depends(get_current_user)):
    """Return the decoded text content of a single file."""
    import base64

    token = _require_github_token(current_user)

    params = {"ref": branch} if branch else None
    data = await _github_get(token, f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}", params=params)

    if isinstance(data, dict) and data.get("encoding") == "base64":
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return {"path": path, "content": content}

    raise HTTPException(status_code=400, detail="Could not read file content (not a text file?).")
