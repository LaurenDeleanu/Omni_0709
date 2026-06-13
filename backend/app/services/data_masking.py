import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("successcore.masking")

SENSITIVE_FIELDS = {
    "base_salary": {"mask": "salary_band", "roles_allowed": {"hr_admin", "super_admin"}},
    "social_security_number": {"mask": "full", "roles_allowed": {"hr_admin", "super_admin"}},
    "iban": {"mask": "full", "roles_allowed": {"hr_admin", "super_admin"}},
    "address": {"mask": "full", "roles_allowed": {"hr_admin", "super_admin", "employee"}},
    "phone_number": {"mask": "partial", "roles_allowed": {"hr_admin", "super_admin", "manager"}},
}

def _salary_to_band(value: float) -> str:
    if value <= 0:
        return "N/A"
    bands = [(30000, "€30-50k"), (50000, "€30-50k"), (60000, "€50-80k"), (80000, "€80-120k"), (float("inf"), "€120k+")]
    for cap, label in bands:
        if value < cap:
            return label
    return "€120k+"


def mask_data(data: Dict[str, Any], user_roles: List[str], own_email: Optional[str] = None) -> Dict[str, Any]:
    if "hr_admin" in user_roles or "super_admin" in user_roles:
        return data

    is_manager = "manager" in user_roles
    is_employee = "employee" in user_roles
    is_self = own_email and data.get("email") == own_email
    is_self_or_admin = is_self or is_manager

    masked = dict(data)
    for field, rules in SENSITIVE_FIELDS.items():
        if field not in masked:
            continue
        allowed = rules["roles_allowed"]
        if is_self and field in {"base_salary", "phone_number", "address"}:
            continue
        if any(r in user_roles for r in allowed) if not is_self else False:
            continue
        mask_type = rules["mask"]
        value = masked[field]
        if value is None:
            continue
        if mask_type == "salary_band":
            if isinstance(value, (int, float)):
                masked[field] = _salary_to_band(value)
            else:
                masked[field] = "[masked]"
        elif mask_type == "full":
            masked[field] = "[masked]"
        elif mask_type == "partial":
            s = str(value)
            masked[field] = s[:2] + "****" + s[-2:] if len(s) > 4 else "[masked]"

    return masked


def mask_list(data_list: List[Dict[str, Any]], user_roles: List[str], own_email: Optional[str] = None) -> List[Dict[str, Any]]:
    return [mask_data(item, user_roles, own_email) for item in data_list]
