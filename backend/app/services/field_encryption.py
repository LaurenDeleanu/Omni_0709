import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger(__name__)

TEK_PREFIX = "TEK$v1$"

def _get_master_fernet() -> Fernet:
    from app.core.encryption import get_fernet
    return get_fernet()


def generate_tenant_encryption_key(tenant_id: str) -> str:
    tek = Fernet.generate_key().decode()
    wrapped = _get_master_fernet().encrypt(tek.encode()).decode()
    return f"{TEK_PREFIX}{wrapped}"


def _unwrap_tenant_key(wrapped_tek: str) -> str:
    if wrapped_tek.startswith(TEK_PREFIX):
        wrapped = wrapped_tek[len(TEK_PREFIX):]
        return _get_master_fernet().decrypt(wrapped.encode()).decode()
    return wrapped_tek


def encrypt_field(value: str, tenant_tek: Optional[str] = None) -> str:
    if not value:
        return ""
    try:
        if tenant_tek and tenant_tek.startswith(TEK_PREFIX):
            key = _unwrap_tenant_key(tenant_tek)
            f = Fernet(key.encode())
        else:
            f = _get_master_fernet()
        return f.encrypt(value.encode()).decode()
    except Exception as e:
        logger.error(f"Field encryption error: {e}")
        return value


def decrypt_field(cipher_text: str, tenant_tek: Optional[str] = None) -> str:
    if not cipher_text:
        return ""
    try:
        if tenant_tek and tenant_tek.startswith(TEK_PREFIX):
            key = _unwrap_tenant_key(tenant_tek)
            f = Fernet(key.encode())
        else:
            f = _get_master_fernet()
        return f.decrypt(cipher_text.encode()).decode()
    except Exception:
        return cipher_text
