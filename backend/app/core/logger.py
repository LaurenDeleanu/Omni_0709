import logging
import sys
import json
from datetime import datetime, timezone
import contextvars

# Context variables for logging correlation
request_id_var = contextvars.ContextVar("request_id", default="-")
tenant_id_var = contextvars.ContextVar("tenant_id", default="-")

class JSONLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
            "tenant_id": tenant_id_var.get()
        }
        
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)

def setup_logger():
    logger = logging.getLogger("successcore")
    logger.setLevel(logging.INFO)
    
    # Prevenir duplicidad de logs si se llama múltiple veces
    if not logger.handlers:
        formatter = JSONLogFormatter()
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

logger = setup_logger()
