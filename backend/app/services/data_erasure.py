import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text

logger = logging.getLogger("successcore.erasure")

CASCADE_TABLES = [
    "profile_change_requests",
    "employee_history",
    "vacation_requests",
    "time_logs",
    "break_logs",
    "expense_claims",
    "course_enrollments",
    "notifications",
    "kudos",
    "chat_messages",
    "chat_room_members",
    "it_tickets",
    "pay_payslips",
    "agent_execution_runs",
    "user_integrations",
    "push_subscriptions",
    "comments",
]


async def erase_user_data(db: AsyncSession, user_id: str) -> dict:
    from app.models.user import User

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    user_email = user.email
    user_name = user.full_name

    deleted_counts = {}
    for table in CASCADE_TABLES:
        try:
            count_res = await db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE user_id = :uid"),
                {"uid": user_id}
            )
            count = count_res.scalar() or 0
            if count > 0:
                await db.execute(
                    text(f"DELETE FROM {table} WHERE user_id = :uid"),
                    {"uid": user_id}
                )
                deleted_counts[table] = count
        except Exception as e:
            deleted_counts[table] = f"skipped: {e}"

    # Anonymize user record instead of deleting (preserves referential integrity)
    import uuid
    user.email = f"anonymized_{uuid.uuid4().hex[:8]}@deleted.local"
    user.full_name = f"Deleted User ({uuid.uuid4().hex[:6]})"
    user.phone_number = None
    user.address = None
    user.iban = None
    user.social_security_number = None
    user.emergency_contact = None
    user.is_active = False
    user.hashed_password = None
    user.base_salary = 0.0
    user.manager_id = None
    await db.commit()

    logger.info(f"GDPR erasure: user {user_email} ({user_id}) anonymized, {sum(1 for v in deleted_counts.values() if isinstance(v, int))} tables purged")

    return {
        "status": "erased",
        "user_id": user_id,
        "original_email": user_email,
        "original_name": user_name,
        "tables_deleted_from": deleted_counts,
        "total_records_deleted": sum(v for v in deleted_counts.values() if isinstance(v, int)),
    }
