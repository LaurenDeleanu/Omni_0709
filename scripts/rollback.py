#!/usr/bin/env python3
import subprocess
import sys
import os
import time
import json
import urllib.request

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8080")
MAX_WAIT = 120

def run(cmd: str, cwd: str = None) -> tuple:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, cwd=cwd)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"

def rollback_alembic():
    print("[rollback] Downgrading database migration...")
    backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
    rc, out, err = run("alembic downgrade -1", cwd=backend_dir)
    if rc != 0:
        print(f"[rollback] ERROR: {err}")
        return False
    print(f"[rollback] OK: {out}")
    return True

def check_health() -> bool:
    for _ in range(30):
        try:
            r = urllib.request.urlopen(f"{API_URL}/health", timeout=5)
            data = json.loads(r.read())
            if data.get("status") in ("ok", "degraded"):
                return True
        except Exception:
            pass
        time.sleep(2)
    return False

if __name__ == "__main__":
    print(f"Rollback script — {API_URL}")
    if not rollback_alembic():
        print("FAILED: alembic downgrade")
        sys.exit(1)
    if not check_health():
        print("FAILED: health check after rollback")
        sys.exit(1)
    print("Rollback complete — system healthy")
