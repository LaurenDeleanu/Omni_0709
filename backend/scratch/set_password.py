import sqlite3, hashlib, uuid

def hash_password(password):
    salt = uuid.uuid4().hex
    return salt + ':' + hashlib.sha256((password + salt).encode()).hexdigest()

h = hash_password("admin")
conn = sqlite3.connect("successcore.db")

row = conn.execute("SELECT id FROM users WHERE email = ?", ("lauren.deleanu@gmail.com",)).fetchone()
if row:
    conn.execute("UPDATE users SET hashed_password = ?, role = ?, department = ? WHERE email = ?", (h, "hr_admin", "Direccion", "lauren.deleanu@gmail.com"))
    print(f"Updated existing user: {row[0]}")
else:
    uid = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO users (id, email, role, full_name, hashed_password, department, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
        (uid, "lauren.deleanu@gmail.com", "hr_admin", "Admin User", h, "Direccion")
    )
    print(f"Inserted new user: {uid}")

conn.commit()
conn.close()
print("Password set to: admin")
