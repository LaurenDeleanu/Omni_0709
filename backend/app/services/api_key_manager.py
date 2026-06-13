import secrets
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List

logger = logging.getLogger("successcore.apikeys")

_api_keys: Dict[str, dict] = {}


def generate_api_key(user_id: str, tenant_id: str, scopes: List[str], label: str = "") -> dict:
    raw = f"sk-{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw.encode()).hexdigest()

    entry = {
        "key_hash": key_hash,
        "key_prefix": raw[:12],
        "user_id": user_id,
        "tenant_id": tenant_id,
        "scopes": scopes,
        "label": label,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_used": None,
        "revoked": False,
    }
    _api_keys[key_hash] = entry
    logger.info(f"API key created: {key_hash[:12]}... for user {user_id}")

    return {**entry, "api_key": raw}


def validate_api_key(raw_key: str) -> Optional[dict]:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    entry = _api_keys.get(key_hash)
    if not entry or entry["revoked"]:
        return None
    entry["last_used"] = datetime.now(timezone.utc).isoformat()
    return entry


def revoke_api_key(key_hash: str) -> bool:
    entry = _api_keys.get(key_hash)
    if not entry:
        return False
    entry["revoked"] = True
    return True


def rotate_api_key(key_hash: str) -> Optional[dict]:
    entry = _api_keys.get(key_hash)
    if not entry or entry["revoked"]:
        return None
    entry["revoked"] = True
    return generate_api_key(entry["user_id"], entry["tenant_id"], entry["scopes"], entry.get("label", ""))


def list_user_keys(user_id: str) -> List[dict]:
    return [
        {"key_hash": h, "key_prefix": e["key_prefix"], "label": e["label"], "scopes": e["scopes"],
         "created_at": e["created_at"], "last_used": e["last_used"], "revoked": e["revoked"]}
        for h, e in _api_keys.items() if e["user_id"] == user_id
    ]
