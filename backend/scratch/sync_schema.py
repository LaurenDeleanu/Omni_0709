import sqlite3

conn = sqlite3.connect("successcore.db")

# All columns the User model expects vs the restored old DB
missing_columns = {
    "role_id": "VARCHAR",
    "manager_id": "VARCHAR",
    "vacation_allowance": "INTEGER DEFAULT 22",
    "current_debt": "FLOAT DEFAULT 0",
    "base_salary": "FLOAT DEFAULT 0",
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
}

# Get existing columns
cols = conn.execute("PRAGMA table_info(users)").fetchall()
existing = {c[1] for c in cols}

for col, dtype in missing_columns.items():
    if col not in existing:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {dtype}")
            print(f"Added column: {col} ({dtype})")
        except Exception as e:
            print(f"Failed to add {col}: {e}")

conn.commit()
conn.close()
print("Schema sync complete")
