import sqlite3
import sys
sys.path.insert(0, ".")
from app.core.auth import hash_password

mvp = sqlite3.connect("successcore.db")
mod = sqlite3.connect("successcore_mod.db")

# --- 1. Add missing columns to MVP users table ---
missing = {
    "role_id": "VARCHAR", "manager_id": "VARCHAR", "vacation_allowance": "INTEGER DEFAULT 22",
    "current_debt": "FLOAT DEFAULT 0", "base_salary": "FLOAT DEFAULT 0",
    "country": "VARCHAR DEFAULT 'ES'", "timezone": "VARCHAR DEFAULT 'Europe/Madrid'",
    "currency": "VARCHAR DEFAULT 'EUR'", "locale": "VARCHAR DEFAULT 'es'",
    "phone_number": "VARCHAR", "address": "VARCHAR", "iban": "VARCHAR",
    "social_security_number": "VARCHAR", "emergency_contact": "VARCHAR",
    "contract_type": "VARCHAR DEFAULT 'indefinido'", "hire_date": "VARCHAR",
    "custom_fields": "TEXT", "is_super_admin": "BOOLEAN DEFAULT 0",
}
existing = {c[1] for c in mvp.execute("PRAGMA table_info(users)").fetchall()}
for col, dtype in missing.items():
    if col not in existing:
        try:
            mvp.execute(f"ALTER TABLE users ADD COLUMN {col} {dtype}")
            print(f"Added users.{col}")
        except Exception as e:
            print(f"Failed users.{col}: {e}")

# --- 2. Create missing tables in MVP from mod schema ---
mod_tables = {r[0] for r in mod.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
mod_tables.discard("sqlite_sequence")
mvp_tables = set()
try:
    mvp_tables = {r[0] for r in mvp.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
except:
    pass
mvp_tables.discard("sqlite_sequence")

for table in sorted(mod_tables - mvp_tables):
    try:
        cols = [d[1] for d in mod.execute(f"PRAGMA table_info({table})").fetchall()]
        col_defs = ", ".join(f"`{c}` TEXT" for c in cols)
        mvp.execute(f"CREATE TABLE IF NOT EXISTS `{table}` ({col_defs})")
        print(f"Created table: {table}")
    except Exception as e:
        print(f"Failed create {table}: {e}")

# --- 3. Copy all data from mod tables into MVP ---
for table in sorted(mod_tables & {"agents", "agent_configs", "agent_execution_runs", "agent_triggers",
                                    "code_modules", "knowledge_documents", "knowledge_chunks",
                                    "test_suites", "test_cases", "test_runs", "git_repositories",
                                    "workflow_templates", "user_workflows",
                                    "chat_rooms", "chat_room_members", "chat_messages",
                                    "notifications", "announcements", "kudos",
                                    "intel_dashboards", "intel_widgets", "intel_kpi_alerts",
                                    "hire_jobs", "hire_candidates", "hire_interviews",
                                    "sales_leads", "sales_clients",
                                    "pay_cycles", "pay_payslips", "pay_payslip_lines", "pay_bonuses", "pay_tax_rules",
                                    "it_assets", "it_tickets", "saas_licenses", "it_requisitions",
                                    "courses", "course_enrollments", "fundae_validations",
                                    "legal_contracts", "legal_whistleblower_reports", "legal_dsar_tickets",
                                    "ops_assets", "ops_bookings", "ops_visitors",
                                    "grow_objectives", "grow_key_results", "grow_reviews",
                                    "profile_change_requests", "employee_history",
                                    "expense_claims", "time_logs", "journal_entries", "journal_lines",
                                    "teams", "team_members",
                                    "vacation_requests", "meetings", "tasks", "work_schedules",
                                    "work_projects", "work_tasks", "work_boards", "work_columns",
                                    "work_sprints", "work_wiki_pages",
                                    "scheduled_reports", "page_metadata", "tenants",
                                    "roles", "permissions", "role_permissions",
                                    "audit_logs", "comments", "custom_fields",
                                    "push_subscriptions", "user_integrations", "break_logs",
                                    "general_shifts"}):
    try:
        cols = [d[1] for d in mod.execute(f"PRAGMA table_info({table})").fetchall()]
        mvp_cols_list = [c[1] for c in mvp.execute(f"PRAGMA table_info({table})").fetchall()]
        common = [c for c in cols if c in mvp_cols_list]
        if not common:
            continue
        rows = mod.execute(f"SELECT * FROM `{table}`").fetchall()
        count = 0
        for row in rows:
            values = tuple(row[cols.index(c)] for c in common)
            placeholders = ",".join(["?"] * len(common))
            cols_str = ",".join(common)
            mvp.execute(f"INSERT OR IGNORE INTO `{table}` ({cols_str}) VALUES ({placeholders})", values)
            count += 1
        if count > 0:
            print(f"Copied {table}: {count} rows")
    except Exception as e:
        print(f"Skipped {table}: {e}")

# --- 4. Set admin password ---
h = hash_password("admin")
row = mvp.execute("SELECT id FROM users WHERE email = ?", ("lauren.deleanu@gmail.com",)).fetchone()
if row:
    mvp.execute("UPDATE users SET hashed_password = ?, role = 'hr_admin', is_active = 1 WHERE email = ?", (h, "lauren.deleanu@gmail.com"))
    print(f"Updated existing user: {row[0]}")
else:
    mvp.execute(
        "INSERT INTO users (id, email, role, full_name, hashed_password, department, is_active, created_at, updated_at) "
        "VALUES ('admin001', 'lauren.deleanu@gmail.com', 'hr_admin', 'Lauren Deleanu', ?, 'Direccion', 1, datetime('now'), datetime('now'))",
        (h,)
    )
    print("Inserted new user")

mvp.commit()

# Final stats
users = mvp.execute("SELECT COUNT(*) FROM users").fetchone()[0]
agents = mvp.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
plugins = mvp.execute("SELECT COUNT(*) FROM code_modules").fetchone()[0]
rooms = mvp.execute("SELECT COUNT(*) FROM chat_rooms").fetchone()[0]
print(f"\nFINAL: Users={users}  Agents={agents}  Plugins={plugins}  ChatRooms={rooms}")

mvp.close()
mod.close()
print("Merge complete. Run the app now.")
