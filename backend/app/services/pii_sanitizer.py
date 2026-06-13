import re
import logging

logger = logging.getLogger("successcore.pii")

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?<!\d{4}[-/])"                              # negative lookbehind: not preceded by a 4-digit year + separator (avoids dates)
    r"\b"
    r"(?:"
        r"\+\d{1,3}[-.\s]?"                        # international: +XX or +XXX
        r"\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{2,4}"
    r"|"
        r"\(\d{2,4}\)[-.\s]?\d{3,4}[-.\s]?\d{2,4}" # parenthesized area code: (123) 456 7890
    r")"
    r"\b"
)
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CCN_RE = re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b")
DNI_RE = re.compile(r"\b\d{8}[- ]?[A-Z]\b", re.IGNORECASE)
NIE_RE = re.compile(r"\b[XYZ][ -]?\d{7}[ -]?[A-Z]\b", re.IGNORECASE)
CIF_RE = re.compile(r"\b[ABCDEFGHJNPQRSUVW][ -]?\d{7}[ -]?[A-Z0-9]\b", re.IGNORECASE)


def sanitize_output(text: str) -> str:
    if not text:
        return text

    sanitized = EMAIL_RE.sub("[email]", text)
    sanitized = PHONE_RE.sub("[phone]", sanitized)
    sanitized = SSN_RE.sub("[ssn]", sanitized)
    sanitized = CCN_RE.sub("[ccn]", sanitized)
    sanitized = IBAN_RE.sub("[iban]", sanitized)
    sanitized = DNI_RE.sub("[dni]", sanitized)
    sanitized = NIE_RE.sub("[nie]", sanitized)
    sanitized = CIF_RE.sub("[cif]", sanitized)

    return sanitized

