import sys; sys.path.insert(0, ".")
from app.main import app
copilot_routes = [r for r in app.routes if "copilot" in r.path.lower()]
for r in copilot_routes:
    print(f"{getattr(r, 'methods', [])} {r.path}")
