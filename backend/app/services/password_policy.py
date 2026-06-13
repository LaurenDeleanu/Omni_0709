import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger("successcore.password_policy")

DEFAULT_POLICY = {
    "min_length": 8,
    "min_uppercase": 1,
    "min_lowercase": 1,
    "min_digits": 1,
    "min_special": 1,
    "max_repeated_chars": 3,
    "prevent_common": True,
}

COMMON_PASSWORDS = {
    "password", "12345678", "qwerty123", "admin123", "welcome1", "letmein1",
    "password1", "123456789", "football1", "iloveyou1", "monkey123",
}


def validate_password(password: str, policy: Optional[dict] = None) -> Tuple[bool, list]:
    rules = {**DEFAULT_POLICY, **(policy or {})}
    errors = []

    if len(password) < rules["min_length"]:
        errors.append(f"At least {rules['min_length']} characters required")

    uppercase_count = len(re.findall(r"[A-Z]", password))
    if uppercase_count < rules["min_uppercase"]:
        errors.append(f"At least {rules['min_uppercase']} uppercase letter required")

    lowercase_count = len(re.findall(r"[a-z]", password))
    if lowercase_count < rules["min_lowercase"]:
        errors.append(f"At least {rules['min_lowercase']} lowercase letter required")

    digit_count = len(re.findall(r"\d", password))
    if digit_count < rules["min_digits"]:
        errors.append(f"At least {rules['min_digits']} digit required")

    special_count = len(re.findall(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/`~]", password))
    if special_count < rules["min_special"]:
        errors.append(f"At least {rules['min_special']} special character required")

    if rules.get("max_repeated_chars"):
        if re.search(r"(.)\1{" + str(rules["max_repeated_chars"]) + r",}", password):
            errors.append(f"No more than {rules['max_repeated_chars']} repeated characters in a row")

    if rules.get("prevent_common") and password.lower() in COMMON_PASSWORDS:
        errors.append("Password is too common. Choose a stronger one.")

    if rules.get("min_length", 0) > 0 and len(password) < rules["min_length"]:
        errors = [e for e in errors if "characters required" not in e]
        errors.append(f"At least {rules['min_length']} characters required")

    is_valid = len(errors) == 0
    if not is_valid:
        logger.info(f"Password validation failed: {errors}")

    return is_valid, errors
