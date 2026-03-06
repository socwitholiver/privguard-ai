"""Authentication and RBAC helpers for PRIVGUARD AI."""

from __future__ import annotations

from functools import wraps
from typing import Callable, Dict, Optional, Set

from flask import jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash

from config_loader import load_system_config
from security.vault import vault_is_unlocked


SYSTEM_CONFIG = load_system_config()
AUTH_CONFIG = SYSTEM_CONFIG.get("auth", {})
USERS = AUTH_CONFIG.get("users", {})


ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "reviewer": {"scan", "verify", "view_dashboard"},
    "officer": {"scan", "verify", "protect", "view_dashboard"},
    "admin": {
        "scan",
        "verify",
        "protect",
        "view_dashboard",
        "admin_export",
        "admin_cleanup",
    },
}


def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = USERS.get(username)
    if not user:
        return None
    if check_password_hash(user["password_hash"], password):
        return {"username": username, "role": user["role"]}
    return None


def current_user() -> Optional[dict]:
    username = session.get("username")
    role = session.get("role")
    if not username or not role:
        return None
    return {
        "username": username,
        "role": role,
        "display_name": session.get("display_name", username),
        "avatar_url": session.get("avatar_url", ""),
        "theme": session.get("theme", "dark"),
        "vault_unlocked": bool(session.get("vault_unlocked", False) and vault_is_unlocked()),
    }


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_login(view: Callable):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            if request.path.startswith("/api") or request.path.startswith("/scan") or request.path.startswith("/protect"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapper


def require_vault_unlock(view: Callable):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        if not bool(session.get("vault_unlocked", False)) or not vault_is_unlocked():
            session["vault_unlocked"] = False
            if request.path.startswith("/api") or request.path.startswith("/scan") or request.path.startswith("/protect") or request.path.startswith("/automate"):
                return jsonify({"error": "Vault is locked. Log in again with the master password."}), 423
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapper


def require_permission(permission: str):
    def decorator(view: Callable):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            if not has_permission(user["role"], permission):
                return jsonify({"error": "Insufficient permission"}), 403
            return view(*args, **kwargs)

        return wrapper

    return decorator
