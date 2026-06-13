#!/usr/bin/env python3
import subprocess
import sys
import time
import json
import urllib.request
import os

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8080")
MAX_RETRIES = 30
RETRY_DELAY = 2

def check_health() -> dict:
    try:
        r = urllib.request.urlopen(f"{API_URL}/health", timeout=5)
        return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def run_smoke_tests() -> bool:
    tests = [
        ("GET", "/health"),
        ("GET", "/api/v1/users/csrf-token"),
    ]
    for method, endpoint in tests:
        try:
            req = urllib.request.Request(f"{API_URL}{endpoint}", method=method)
            r = urllib.request.urlopen(req, timeout=10)
            if r.status != 200:
                print(f"FAIL {method} {endpoint} → {r.status}")
                return False
        except Exception as e:
            print(f"FAIL {method} {endpoint} → {e}")
            return False
    return True

def wait_for_ready() -> bool:
    for i in range(1, MAX_RETRIES + 1):
        health = check_health()
        status = health.get("status", "unknown")
        db_ok = health.get("checks", {}).get("database", {}).get("ok", False)
        if status in ("ok", "degraded") and db_ok:
            print(f"Ready (attempt {i}): status={status} db={db_ok}")
            return True
        print(f"Waiting ({i}/{MAX_RETRIES}): {status}")
        time.sleep(RETRY_DELAY)
    return False

if __name__ == "__main__":
    print(f"Deploy smoke test — {API_URL}")
    if not wait_for_ready():
        print("FAILED: health check never passed")
        sys.exit(1)
    if not run_smoke_tests():
        print("FAILED: smoke tests")
        sys.exit(1)
    print("PASSED: all smoke tests")
