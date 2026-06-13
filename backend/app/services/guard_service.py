import re
import logging
from typing import Tuple

logger = logging.getLogger("successcore.guard")

# ---- English injection patterns (original 15) ----
INJECTION_PATTERNS_EN = [
    r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|directives?)",
    r"(?i)forget\s+(all\s+)?(previous|your)\s+(instructions?|training|prompts?)",
    r"(?i)you\s+are\s+now\s+(DAN|STAN|jailbroken|in\s+developer\s+mode)",
    r"(?i)pretend\s+(you\s+are|to\s+be)\s+(a\s+)?(different|another)\s+(AI|assistant|model)",
    r"(?i)system\s*:\s*(you\s+are|now\s+you)",
    r"(?i)new\s+system\s+prompt",
    r"(?i)override\s+(system|safety)\s+(instructions?|prompts?|rules?)",
    r"(?i)bypass\s+(your\s+)?(restrictions?|guardrails?|safety|filters?)",
    r"(?i)output\s+your\s+(system\s+)?prompt",
    r"(?i)reveal\s+(your\s+)?(instructions?|system\s+prompt|training\s+data)",
    r"(?i)what\s+(was|is|were)\s+your\s+(system\s+)?(prompt|instructions)",
    r"(?i)from\s+now\s+on\s+you\s+(are|will\s+be)\s+(a\s+)?(different|another)",
    r"(?i)act\s+as\s+if\s+you\s+(are|were)\s+(a\s+)?(different|hacked|unrestricted)",
    r"(?i)do\s+not\s+follow\s+(your\s+)?(ethics|guidelines|rules|policy)",
    r"(?i)respond\s+in\s+a\s+way\s+that\s+(violates|breaks|ignores)",
]

# ---- Spanish injection patterns (15 mirrors) ----
INJECTION_PATTERNS_ES = [
    r"(?i)ignora\s+(todas?\s+)?(las\s+)?(instrucciones|directivas|indicaciones)\s+(previas|anteriores)",
    r"(?i)olvida\s+(todas?\s+)?(tus\s+)?(instrucciones|entrenamiento|directivas)",
    r"(?i)ahora\s+eres\s+(un\s+)?(otro|diferente)\s+(asistente|modelo|IA)",
    r"(?i)finge\s+(que\s+)?(eres|ser)\s+(un\s+)?(otro|diferente)\s+(asistente|modelo|IA)",
    r"(?i)sistema\s*:\s*(ahora\s+eres|t[úu]\s+eres)",
    r"(?i)nuevo\s+prompt\s+de\s+sistema",
    r"(?i)sobrescri(be|bir)\s+(las?\s+)?(instrucciones|reglas|directivas)\s+(del\s+sistema|de\s+seguridad)",
    r"(?i)(salta|evita|elude)\s+(tus\s+)?(restricciones|filtros|guardarraíles|seguridad)",
    r"(?i)(muestra|dame|escribe)\s+(tu\s+)?prompt\s+(del\s+sistema|interno)",
    r"(?i)(revela|muestra|dime)\s+(tus\s+)?(instrucciones|prompt\s+del?\s+sistema|datos\s+de\s+entrenamiento)",
    r"(?i)cu[áa]l(es)?\s+(es|son|eran?)\s+tus?\s+(instrucciones|prompt)",
    r"(?i)a\s+partir\s+de\s+ahora\s+(eres|ser[áa]s)\s+(un\s+)?(otro|diferente)",
    r"(?i)act[úu]a\s+como\s+si\s+(fueras|fueses)\s+(un\s+)?(otro|hackeado|sin\s+restricciones)",
    r"(?i)no\s+sigas\s+(tus\s+)?(reglas|[ée]tica|directrices|pol[ií]ticas?)",
    r"(?i)responde\s+de\s+(una\s+)?forma\s+que\s+(viole|rompa|ignore)",
]

INJECTION_PATTERNS = INJECTION_PATTERNS_EN + INJECTION_PATTERNS_ES

SENSITIVE_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN-like"),
    (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "CCN-like"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL"),
    (r"\b(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b", "IP"),
]

BLOCKED_PREFIXES = ["/", "\\", "!", "`", "$", "|"]


def detect_injection(message: str) -> Tuple[bool, str]:
    msg_lower = message.lower().strip()

    for prefix in BLOCKED_PREFIXES:
        if msg_lower.startswith(prefix + "system") or msg_lower.startswith(prefix + "prompt"):
            return True, f"Blocked command-like prefix: '{message[:30]}...'"

    for pattern in INJECTION_PATTERNS:
        match = re.search(pattern, message)
        if match:
            return True, f"Potential prompt injection detected: '{match.group(0)}'"

    return False, ""


def detect_pii_in_output(text: str) -> Tuple[bool, list]:
    findings = []
    for pattern, pii_type in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            if pii_type == "EMAIL":
                findings.extend([m for m in matches])
            elif pii_type == "IP":
                findings.extend([m for m in matches])
    return len(findings) > 0, findings
