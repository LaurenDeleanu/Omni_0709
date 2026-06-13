#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

async def main():
    from app.core.database import AsyncSessionGlobal
    from app.services.field_encryption import encrypt_field, decrypt_field, generate_tenant_encryption_key

    async with AsyncSessionGlobal() as db:
        print("Re-encryption migration: scanning for plaintext data...")
        from sqlalchemy import text

        result = await db.execute(text(
            "SELECT id, address, iban, social_security_number FROM tenant_acme_corp.users"
        ))
        rows = result.all()
        re_encrypted = 0
        for row in rows:
            uid, address, iban, ssn = row
            updated = False
            for col, val, col_name in [(address, None, "address"), (iban, None, "iban"), (ssn, None, "social_security_number")]:
                if not col:
                    continue
                try:
                    decrypted = decrypt_field(col)
                    if decrypted == col:
                        encrypted = encrypt_field(col)
                        await db.execute(text(
                            f"UPDATE tenant_acme_corp.users SET {col_name} = :val WHERE id = :uid"
                        ), {"val": encrypted, "uid": uid})
                        updated = True
                except Exception:
                    pass
            if updated:
                re_encrypted += 1

        if re_encrypted:
            await db.execute(text("COMMIT"))
        print(f"Re-encrypted {re_encrypted} records")
        print("Migration complete")

asyncio.run(main())
