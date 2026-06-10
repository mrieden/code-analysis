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
# ── Google OAuth (scaffolded) ───────────────────────────────────
# Drop GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET into your .env to activate.
# No code changes are needed once those creds exist.
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
BACKEND_URL          = os.getenv("BACKEND_URL", "http://localhost:8000")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", f"{BACKEND_URL}/auth/google/callback")
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
async def github_login(link_token: str = ""):
    """Redirect user to GitHub OAuth page.

    If `link_token` (a logged-in user's JWT) is supplied, it is passed through
    the OAuth `state` param so the callback can LINK GitHub to that existing
    account (used by Google users pressing "Connect to GitHub") instead of
    creating a separate standalone GitHub account.
    """
    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&scope=read:user,user:email,repo"
        f"&state={link_token}"
    )
    return RedirectResponse(github_url)


@router.get("/auth/github/callback")
async def github_callback(code: str, state: str = ""):
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

    # 2b. LINK MODE — a logged-in user (e.g. a Google user) is connecting GitHub.
    #     `state` carries their existing JWT, so we attach the GitHub token to
    #     THAT account instead of creating a separate GitHub-only account. Their
    #     identity (and therefore their history) stays the same.
    linked_user = None
    if state:
        try:
            linked_user = await decode_token(state)
        except Exception:
            linked_user = None

    if linked_user:
        # MERGE history: if this GitHub account previously existed on its own,
        # move its past history onto THIS account so the user sees their old
        # GitHub history together with their current (e.g. Google) history.
        # Then drop the now-redundant standalone GitHub user doc.
        if str(github_id) != str(linked_user["github_id"]):
            await db.history.update_many(
                {"user_id": str(github_id)},
                {"$set": {"user_id": str(linked_user["github_id"])}},
            )
            await db.users.delete_one({"github_id": str(github_id)})

        await db.users.update_one(
            {"github_id": linked_user["github_id"]},
            {"$set": {
                "github_access_token": access_token,
                "github_username": github_username,
                "github_linked_id": github_id,
                "github_connected": True,
                "last_login": datetime.utcnow(),
            }},
        )
        # Reuse the same identity for the JWT so nothing about the user changes.
        jwt_token = create_token(linked_user["github_id"], linked_user.get("username", github_username))
        return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={jwt_token}&connected=github")

    # 2c. REVERSE LINK: if this GitHub account was previously linked to another
    #     account (e.g. a Google user pressed "Connect to GitHub"), sign the user
    #     into THAT merged account so their unified history stays intact, instead
    #     of splitting back out into a separate GitHub-only identity.
    existing_link = await db.users.find_one({"github_linked_id": github_id})
    if existing_link:
        await db.users.update_one(
            {"github_id": existing_link["github_id"]},
            {"$set": {
                "github_access_token": access_token,
                "github_username": github_username,
                "github_connected": True,
                "last_login": datetime.utcnow(),
            }},
        )
        jwt_token = create_token(existing_link["github_id"], existing_link.get("username", github_username))
        return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={jwt_token}")

    # 3. Upsert user in MongoDB (standalone GitHub login)
    await db.users.update_one(
        {"github_id": github_id},
        {"$set": {
            "github_id": github_id,
            "username": github_username,
            "avatar_url": avatar_url,
            "email": email,
            "github_access_token": access_token,
            "auth_provider": "github",
            "last_login": datetime.utcnow(),
        },
         "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True,
    )

    # 4. Create JWT
    jwt_token = create_token(github_id, github_username)

    # 5. Redirect to frontend with token
    return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={jwt_token}")


# ── Google OAuth Routes (scaffold) ─────────────────────────────
# Fully wired. They go live the moment GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
# are present. A Google user is stored with github_id = "google:<sub>", so every
# existing per-user feature (history, JWT, /auth/me) keeps working unchanged.
# GitHub-only features stay gated until the user presses "Connect to GitHub".

@router.get("/auth/google/login")
async def google_login():
    """Redirect user to Google's OAuth consent screen."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured yet.")
    google_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        "&access_type=offline"
        "&prompt=select_account"
    )
    return RedirectResponse(google_url)


@router.get("/auth/google/callback")
async def google_callback(code: str):
    """Exchange Google's code → user info → JWT → redirect to frontend."""
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        raise HTTPException(status_code=503, detail="Google sign-in is not configured yet.")

    # 1. Exchange code for an access token
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    token_data = token_res.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Google OAuth failed")

    # 2. Fetch the Google profile
    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    g = user_res.json()

    user_id  = f"google:{g['id']}"
    username = g.get("name") or g.get("email", "Google User")
    avatar   = g.get("picture", "")
    email    = g.get("email", "")

    # 3. Upsert (same `github_id` primary key → history & per-user features work)
    await db.users.update_one(
        {"github_id": user_id},
        {"$set": {
            "github_id": user_id,
            "username": username,
            "avatar_url": avatar,
            "email": email,
            "auth_provider": "google",
            "google_access_token": access_token,
            "last_login": datetime.utcnow(),
        },
         "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True,
    )

    # 4. Issue JWT + redirect
    jwt_token = create_token(user_id, username)
    return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={jwt_token}")


@router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return current logged-in user info."""
    return {
        "github_id":  current_user["github_id"],
        "username":   current_user["username"],
        "avatar_url": current_user.get("avatar_url", ""),
        "email":      current_user.get("email", ""),
        "auth_provider":    current_user.get("auth_provider", "github"),
        "github_connected": bool(current_user.get("github_access_token")),
    }


@router.post("/auth/logout")
async def logout():
    """Frontend just deletes the token. This endpoint is a no-op but good practice."""
    return {"message": "Logged out successfully"}


# ── GitHub repo browsing (logged-in users) ────────────────
GITHUB_API = "https://api.github.com"


async def _github_get(token: str, url: str, params=None):
    """Authenticated GET against the GitHub REST API."""
    # Generous timeout so large files / big repositories download fully instead
    # of failing mid-scan. Repo scanning relies on this never timing out early.
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0)) as client:
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
