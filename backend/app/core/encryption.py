import logging
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger(__name__)

_fernet_instance = None

def get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance
    key = settings.ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY is not configured. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
            "and add it to your .env file as ENCRYPTION_KEY=<generated_key>"
        )
    try:
        _fernet_instance = Fernet(key.encode())
    except Exception as e:
        raise RuntimeError(f"Invalid ENCRYPTION_KEY: {e}") from e
    return _fernet_instance

def encrypt_key(plain_text: str) -> str:
    if not plain_text:
        return ""
    try:
        f = get_fernet()
        return f.encrypt(plain_text.encode()).decode()
    except Exception as e:
        logger.error(f"encryption error: {e}")
        return plain_text

def decrypt_key(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    try:
        f = get_fernet()
        return f.decrypt(cipher_text.encode()).decode()
    except Exception:
        return cipher_text
