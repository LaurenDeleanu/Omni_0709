lines = open("app/api/v1/ai.py").readlines()
for i in range(168, min(297, len(lines))):
    stripped = lines[i].rstrip()
    if stripped.strip():
        indent = len(lines[i]) - len(lines[i].lstrip())
        print(f"{i+1:4d} |{indent:3d} spaces| {stripped.strip()[:80]}")
