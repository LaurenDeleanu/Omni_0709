import sqlite3
conn = sqlite3.connect("successcore.db")
users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
plugins = conn.execute("SELECT COUNT(*) FROM code_modules").fetchone()[0]
rooms = conn.execute("SELECT COUNT(*) FROM chat_rooms").fetchone()[0]
tables = len(conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
print(f"Users: {users}  Agents: {agents}  Plugins: {plugins}  Chat Rooms: {rooms}  Tables: {tables}")
conn.close()
