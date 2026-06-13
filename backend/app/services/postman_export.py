import json
import logging

logger = logging.getLogger("successcore.postman")


def generate_postman_collection(openapi_spec: dict) -> dict:
    info = openapi_spec.get("info", {})
    servers = openapi_spec.get("servers", [])
    base_url = servers[0]["url"] if servers else "http://localhost:8080"

    items = []
    for path, methods in openapi_spec.get("paths", {}).items():
        for method, details in methods.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            item = {
                "name": details.get("summary", f"{method.upper()} {path}"),
                "request": {
                    "method": method.upper(),
                    "header": [{"key": "Authorization", "value": "Bearer {{accessToken}}", "type": "text"}, {"key": "Content-Type", "value": "application/json"}],
                    "url": {"raw": f"{base_url}{path}", "host": [base_url.split("://")[1]], "path": path.strip("/").split("/")},
                }
            }
            if details.get("requestBody"):
                item["request"]["body"] = {"mode": "raw", "raw": "{}"}
            items.append(item)

    return {
        "info": {
            "name": info.get("title", "SuccessCore API"),
            "description": info.get("description", ""),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [{"key": "accessToken", "value": "", "type": "string"}],
        "item": items,
    }
