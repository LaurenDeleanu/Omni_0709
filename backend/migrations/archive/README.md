# Migration Scripts Archive

This directory contains legacy manual migration scripts that have been superseded by Alembic revisions.

**Do not run these scripts directly.** Use `alembic upgrade head` instead.

## Migration History (Chronological)

| Script | Purpose | Alembic Equivalent |
|--------|---------|-------------------|
| create_tables.py | Initial table creation | Base.metadata.create_all() in 0a1913327c5e |
| migrate_phase2.py | Phase 2 schema changes | Merged into Alembic revision chain |
| migrate_phase3.py | Phase 3 additions | Merged into Alembic revision chain |
| migrate_phase4.py | Phase 4 expansions | Merged into Alembic revision chain |
| migrate_phase6.py | Phase 6 changes | Merged into Alembic revision chain |
| migrate_phase7.py | Phase 7 updates | Merged into Alembic revision chain |
| migrate_phase8.py | Phase 8 core | Merged into Alembic revision chain |
| migrate_phase8_part2.py | Phase 8 part 2 | Merged into Alembic revision chain |
| migrate_phase8_profile.py | Profile change requests | Merged into Alembic revision chain |
| migrate_hire.py | Recruitment ATS tables | Merged into Alembic revision chain |
| migrate_legal.py | Legal & compliance tables | Merged into Alembic revision chain |
| migrate_new_modules.py | New module tables | Merged into Alembic revision chain |
| migrate_pay.py | Payroll tables | Merged into Alembic revision chain |
| migrate_sales.py | CRM tables | Merged into Alembic revision chain |
| migrate_users_pay.py | User pay fields | Merged into Alembic revision chain |
| migrate_work.py | Project management tables | Merged into Alembic revision chain |
| manual_migrate.py | Manual migration runner | Replaced by `alembic upgrade head` |
| make_admin.py | Create admin user utility | Use tenant provisioning API or scripts/seed.py |
| seed_rbac.py | Seed RBAC data | Replaced by tenant_provisioning.py seed logic |

## Current Alembic Revisions

```
idx_performance_v1 (HEAD)
  - Add 28 performance indexes across 15 tables
  - Depends on: cedbdecaecce

cedbdecaecce
  - Add metadata table

3c2890cff5e3
  - Add scheduled_report model

0a1913327c5e
  - Add calendar tables (vacation_requests, meetings, tasks)
```

## Adding New Migrations

```bash
cd backend
alembic revision -m "description of change"
# Edit the generated file in alembic/versions/
alembic upgrade head
```
