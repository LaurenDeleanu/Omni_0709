import logging
from typing import List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("successcore.feature_flags")

DEFAULT_FLAGS = {
    "ai_agents": True,
    "chat": True,
    "calendar": True,
    "training": True,
    "hire": True,
    "finance": True,
    "pay": True,
    "legal": True,
    "work": True,
    "sales": True,
    "ops": True,
    "grow": True,
    "intelligence": True,
    "kudos": True,
    "announcements": True,
    "workflows": True,
    "integrations": True,
    "crm": True,
    "git": True,
    "monitoring": True,
    "billing": True,
    "beta_features": False,
}

_tenant_flags: dict = {}


def get_flags(tenant_id: str) -> dict:
    defaults = dict(DEFAULT_FLAGS)
    overrides = _tenant_flags.get(tenant_id, {})
    defaults.update(overrides)
    return defaults


def set_flag(tenant_id: str, flag: str, enabled: bool) -> dict:
    if tenant_id not in _tenant_flags:
        _tenant_flags[tenant_id] = {}
    _tenant_flags[tenant_id][flag] = enabled
    return {"tenant_id": tenant_id, "flag": flag, "enabled": enabled}


def is_module_enabled(tenant_id: str, module_name: str) -> bool:
    flags = get_flags(tenant_id)
    return flags.get(module_name, True)
