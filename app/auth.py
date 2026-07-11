"""简易账号鉴权：管理员 / 研判员 Token。

修改原因：全系统安全加固——仪表盘与高权限 API 必须登录。
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

_bearer = HTTPBearer(auto_error=False)
# token -> {user, role, exp}
_TOKENS: dict[str, dict] = {}


def _hash_pw(pw: str) -> str:
    return hashlib.sha256((pw or "").encode("utf-8")).hexdigest()


def auth_enabled() -> bool:
    return bool(getattr(get_settings(), "auth_enabled", True))


def verify_login(username: str, password: str) -> Optional[dict]:
    s = get_settings()
    users = {
        getattr(s, "auth_admin_user", "admin"): ("admin", getattr(s, "auth_admin_password", "")),
        getattr(s, "auth_analyst_user", "analyst"): ("analyst", getattr(s, "auth_analyst_password", "")),
    }
    if username not in users:
        return None
    role, pw = users[username]
    if not pw or not hmac.compare_digest(_hash_pw(password), _hash_pw(pw)):
        # 明文比对（部署配置为明文密码）
        if password != pw:
            return None
    return {"username": username, "role": role}


def issue_token(user: dict, ttl_sec: int = 86400) -> str:
    tok = secrets.token_urlsafe(32)
    _TOKENS[tok] = {**user, "exp": time.time() + ttl_sec}
    return tok


def revoke_token(token: str) -> None:
    _TOKENS.pop(token, None)


def current_user(
    request: Request,
    cred: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[dict]:
    if not auth_enabled():
        return {"username": "anonymous", "role": "admin"}  # 本地关闭鉴权时放行
    token = None
    if cred and cred.credentials:
        token = cred.credentials
    if not token:
        token = request.cookies.get("mn_auth_token")
    if not token or token not in _TOKENS:
        return None
    info = _TOKENS[token]
    if info.get("exp", 0) < time.time():
        _TOKENS.pop(token, None)
        return None
    return info


def require_login(user: Optional[dict] = Depends(current_user)) -> dict:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return user


def require_admin(user: dict = Depends(require_login)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user
