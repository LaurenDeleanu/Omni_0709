import httpx
import sys

print("Making diagnostic HTTP requests...")
try:
    # 1. Health check
    r = httpx.get("http://127.0.0.1:8000/health")
    status_health = r.status_code
    body_health = r.text
except Exception as e:
    status_health = "ERROR"
    body_health = str(e)

try:
    # 2. Try notifications
    r = httpx.get("http://127.0.0.1:8000/api/v1/notifications")
    status_notif = r.status_code
    body_notif = r.text
except Exception as e:
    status_notif = "ERROR"
    body_notif = str(e)

# Write output to test_http.txt
with open("test_http.txt", "w", encoding="utf-8") as f:
    f.write(f"Health status: {status_health}\n")
    f.write(f"Health response: {body_health}\n\n")
    f.write(f"Notifications status: {status_notif}\n")
    f.write(f"Notifications response: {body_notif}\n")

print("Diagnostics completed.")
