import subprocess
import shutil
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger("successcore.backup")

DEFAULT_BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backups")


def backup_database(db_url: str = "", backup_dir: str = DEFAULT_BACKUP_DIR) -> str:
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"successcore_backup_{timestamp}.sql"
    filepath = os.path.join(backup_dir, filename)

    target_url = db_url or "postgresql://postgres:password@localhost:5432/successcore"

    try:
        parsed = target_url.replace("postgresql://", "").replace("postgres://", "").replace("+asyncpg", "")
        if "@" in parsed:
            creds_host = parsed.split("@")
            user_pass = creds_host[0].split(":")
            host_db = creds_host[1].split("/")
            user = user_pass[0]
            password = user_pass[1] if len(user_pass) > 1 else ""
            host_port = host_db[0].split(":")
            host = host_port[0]
            port = host_port[1] if len(host_port) > 1 else "5432"
            database = host_db[1] if len(host_db) > 1 else "successcore"

            env = os.environ.copy()
            env["PGPASSWORD"] = password

            cmd = [
                "pg_dump",
                "-h", host,
                "-p", port,
                "-U", user,
                "-d", database,
                "-f", filepath,
                "--no-owner",
                "--no-acl",
            ]
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                _verify_backup = _check_backup_integrity(filepath)
                logger.info(f"Database backup created: {filepath} ({size_mb:.1f} MB) integrity={_verify_backup}")
                return filepath
            else:
                raise RuntimeError(f"pg_dump failed: {result.stderr}")
        else:
            raise ValueError("Could not parse database URL")
    except FileNotFoundError:
        logger.warning("pg_dump not found in PATH. Install PostgreSQL client tools.")
        fallback_path = os.path.join(backup_dir, timestamp)
        os.makedirs(fallback_path, exist_ok=True)
        return fallback_path
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise


def _check_backup_integrity(filepath: str) -> bool:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(200)
            return "--" in head and "PostgreSQL" in head
    except Exception:
        return False


def verify_backup(filepath: str) -> dict:
    if not os.path.exists(filepath):
        return {"valid": False, "reason": "File not found"}
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    integrity = _check_backup_integrity(filepath)
    return {"valid": integrity, "file": filepath, "size_mb": round(size_mb, 2)}


def list_backups(backup_dir: str = DEFAULT_BACKUP_DIR) -> list:
    if not os.path.exists(backup_dir):
        return []
    backups = []
    for f in sorted(os.listdir(backup_dir), reverse=True):
        full = os.path.join(backup_dir, f)
        if os.path.isfile(full):
            size_mb = os.path.getsize(full) / (1024 * 1024)
            backups.append({"filename": f, "size_mb": round(size_mb, 2), "path": full})
    return backups
