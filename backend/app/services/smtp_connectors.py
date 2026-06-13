import logging

logger = logging.getLogger("successcore.smtp_connectors")

SMTP_CONFIGS = {
    "outlook": {"host": "smtp.office365.com", "port": 587, "tls": True},
    "zoho": {"host": "smtp.zoho.com", "port": 587, "tls": True},
    "google": {"host": "smtp.gmail.com", "port": 587, "tls": True},
    "generic": {"host": "smtp.gmail.com", "port": 587, "tls": True},
}


def get_smtp_config(provider: str) -> dict:
    return SMTP_CONFIGS.get(provider.lower(), SMTP_CONFIGS["generic"])


IMAP_CONFIGS = {
    "outlook": {"host": "outlook.office365.com", "port": 993, "ssl": True},
    "zoho": {"host": "imap.zoho.com", "port": 993, "ssl": True},
    "google": {"host": "imap.gmail.com", "port": 993, "ssl": True},
}
