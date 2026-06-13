import logging
from typing import Dict, Any

logger = logging.getLogger("successcore.sessions")

_active_sessions: Dict[str, dict] = {}


def register_session(token_jti: str, user_email: str, user_id: str, ip: str = "") -> None:
    _active_sessions[token_jti] = {
        "jti": token_jti,
        "user_email": user_email,
        "user_id": user_id,
        "ip": ip,
    }


def revoke_session(token_jti: str) -> bool:
    if token_jti in _active_sessions:
        del _active_sessions[token_jti]
        return True
    return False


def is_session_revoked(token_jti: str) -> bool:
    return token_jti in _active_sessions


def list_sessions(user_id: str = "", user_email: str = "") -> list:
    results = []
    for jti, data in _active_sessions.items():
        if user_id and data["user_id"] != user_id:
            continue
        if user_email and data["user_email"] != user_email:
            continue
        results.append(data)
    return results


def get_session_count() -> int:
    return len(_active_sessions)
