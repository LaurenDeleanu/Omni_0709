import sqlite3
import sys
sys.path.insert(0, ".")

from app.core.auth import hash_password

conn = sqlite3.connect("successcore.db")

# 1. Add missing columns the current User model expects
missing = {
    "role_id": "VARCHAR",
    "manager_id": "VARCHAR",
    "vacation_allowance": "INTEGER DEFAULT 22",
    "current_debt": "FLOAT DEFAULT 0",
    "base_salary": "FLOAT DEFAULT 0",
    "country": "VARCHAR DEFAULT 'ES'",
    "timezone": "VARCHAR DEFAULT 'Europe/Madrid'",
    "currency": "VARCHAR DEFAULT 'EUR'",
    "locale": "VARCHAR DEFAULT 'es'",
    "phone_number": "VARCHAR",
    "address": "VARCHAR",
    "iban": "VARCHAR",
    "social_security_number": "VARCHAR",
    "emergency_contact": "VARCHAR",
    "contract_type": "VARCHAR DEFAULT 'indefinido'",
    "hire_date": "VARCHAR",
    "custom_fields": "TEXT",
    "is_super_admin": "BOOLEAN DEFAULT 0",
}
cols = {c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()}
for col, dtype in missing.items():
    if col not in cols:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {dtype}")
            print(f"Added column: {col}")
        except Exception as e:
            print(f"Failed {col}: {e}")

# 2. Set password for admin user
h = hash_password("admin")
# Update existing if already present
conn.execute(
    "UPDATE users SET hashed_password = ?, role = 'hr_admin' WHERE email = 'lauren.deleanu@gmail.com'",
    (h,)
)
if conn.execute("SELECT 1 FROM users WHERE email = 'lauren.deleanu@gmail.com'").fetchone():
    print("Updated existing user lauren.deleanu@gmail.com")
else:
    conn.execute(
        "INSERT INTO users (id, email, role, full_name, hashed_password, department, is_active, created_at, updated_at) "
        "VALUES ('admin001', 'lauren.deleanu@gmail.com', 'hr_admin', 'Lauren Deleanu', ?, 'Direccion', 1, datetime('now'), datetime('now'))",
        (h,)
    )
    print("Inserted new user lauren.deleanu@gmail.com")
conn.execute(
    "UPDATE users SET hashed_password = ?, role = 'hr_admin', is_active = 1 WHERE email = 'lauren.deleanu@gmail.com'",
    (h,)
)
conn.commit()

# Verify
row = conn.execute("SELECT id, email, role, hashed_password FROM users WHERE email = 'lauren.deleanu@gmail.com'").fetchone()
print(f"User: {row}")
conn.close()
print("Original DB restored with password set and schema synced.")
print("Login: lauren.deleanu@gmail.com / admin")
