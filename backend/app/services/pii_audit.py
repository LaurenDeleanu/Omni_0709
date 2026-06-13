import logging
from typing import List, Set, Dict, Any

logger = logging.getLogger("successcore.pii_audit")

PII_FIELDS: Set[str] = {
    "bank_account", "iban", "swift", "routing_number",
    "ssn", "social_security", "tax_id", "nif", "nie", "dni",
    "passport_number", "driver_license",
    "phone_number", "mobile", "personal_phone",
    "home_address", "personal_address", "residence",
    "emergency_contact", "emergency_phone",
    "health_insurance", "medical_info",
    "base_salary", "salary", "compensation",
    "marital_status", "dependents",
}

PII_MODELS = {
    "user": {"phone", "address"},
    "employee": {"ssn", "tax_id", "bank_account", "home_address", "base_salary", "national_id", "passport_number", "emergency_contact", "marital_status"},
    "pay": {"iban", "swift", "base_salary", "bonus_amount"},
    "candidate": {"phone", "email_personal", "address", "current_salary"},
}

ENCRYPTED_PREFIX = "ENC:"


def is_pii_field(field_name: str, model_name: str = "") -> bool:
    field_lower = field_name.lower().replace("_", "")
    for pii in PII_FIELDS:
        if pii.replace("_", "") in field_lower:
            return True
    if model_name and model_name.lower() in PII_MODELS:
        model_fields = PII_MODELS[model_name.lower()]
        return field_name.lower() in model_fields
    return False


def get_pii_fields_for_model(model_name: str) -> Set[str]:
    return PII_MODELS.get(model_name.lower(), set())


def mask_pii_value(value: str, visible_chars: int = 4) -> str:
    if not value or len(value) <= visible_chars:
        return value
    return value[:visible_chars] + "*" * (len(value) - visible_chars)


def audit_model_for_pii(model_name: str, fields: Dict[str, Any]) -> List[Dict[str, str]]:
    findings = []
    expected_pii = get_pii_fields_for_model(model_name)
    encrypted_fields = []
    unencrypted_pii = []
    for field_name, value in fields.items():
        if field_name in expected_pii:
            if isinstance(value, str) and value.startswith(ENCRYPTED_PREFIX):
                encrypted_fields.append(field_name)
            elif value is not None and value != "":
                unencrypted_pii.append(field_name)
    if unencrypted_pii:
        findings.append({
            "model": model_name,
            "issue": "unencrypted_pii",
            "severity": "HIGH",
            "fields": unencrypted_pii,
        })
    if encrypted_fields:
        findings.append({
            "model": model_name,
            "issue": "encrypted_pii",
            "severity": "OK",
            "fields": encrypted_fields,
        })
    return findings
