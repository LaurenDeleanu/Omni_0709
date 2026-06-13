import logging
from app.services.event_bus import get_event_bus

logger = logging.getLogger("successcore.event_notif")

NOTIFICATION_TEMPLATES = {
    "employee.created": {"title": "New team member!", "message": "{name} has joined as {role} in {department}"},
    "vacation.approved": {"title": "Vacation approved", "message": "Your vacation ({start} to {end}) has been approved"},
    "course.completed": {"title": "Course completed!", "message": "You completed {title}"},
    "kudos.received": {"title": "You received Kudos!", "message": "{sender} gave you kudos: {message}"},
    "expense.approved": {"title": "Expense approved", "message": "Your expense claim for {amount} was approved"},
    "onboarding.completed": {"title": "Onboarding complete!", "message": "Onboarding plan generated: {plan_summary}"},
}


async def _handle_hr_event(tenant_id: str, payload: dict, event_type: str = ""):
    try:
        template = NOTIFICATION_TEMPLATES.get(event_type)
        if not template:
            return

        user_id = payload.get("user_id") or payload.get("receiver_id")
        if not user_id:
            return

        title = template["title"]
        try:
            message = template["message"].format(**payload)
        except KeyError:
            message = template["message"]

        from app.services.notification_utils import _push_via_ws
        notif = type("Notif", (), {
            "id": f"event-{event_type}",
            "title": title,
            "message": message,
            "type": "event",
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        })
        await _push_via_ws(user_id, notif)
    except Exception as e:
        logger.debug(f"Event→notification bridge: {e}")


async def _slack_vacation_approved(tenant_id: str, payload: dict):
    try:
        user_id = payload.get("user_id", "")
        from sqlalchemy import select
        from app.core.database import AsyncSessionGlobal
        async with AsyncSessionGlobal() as db:
            from app.models.user import User
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user and user.email:
                from app.services.slack_connector import notify_vacation_approved
                await notify_vacation_approved(
                    user_email=user.email,
                    start_date=payload.get("start_date", ""),
                    end_date=payload.get("end_date", ""),
                )
    except Exception as e:
        logger.debug(f"Slack vacation notification failed: {e}")


async def _slack_kudos_received(tenant_id: str, payload: dict):
    try:
        receiver_id = payload.get("receiver_id", "")
        sender_id = payload.get("sender_id", "")
        badge = payload.get("badge", "Kudos")
        message = payload.get("message", "")
        from sqlalchemy import select
        from app.core.database import AsyncSessionGlobal
        async with AsyncSessionGlobal() as db:
            from app.models.user import User

            sender_result = await db.execute(select(User).where(User.id == sender_id))
            sender_user = sender_result.scalar_one_or_none()
            sender_name = sender_user.full_name if sender_user and sender_user.full_name else (sender_user.email if sender_user else "Someone")

            result = await db.execute(select(User).where(User.id == receiver_id))
            user = result.scalar_one_or_none()
            if user and user.email:
                from app.services.slack_connector import notify_kudos_received
                await notify_kudos_received(
                    receiver_email=user.email,
                    sender_name=sender_name,
                    badge=badge,
                    message=message,
                )
    except Exception as e:
        logger.debug(f"Slack kudos notification failed: {e}")


async def _slack_employee_created(tenant_id: str, payload: dict):
    try:
        name = payload.get("full_name", payload.get("name", "New hire"))
        department = payload.get("department", "")
        from app.services.slack_connector import notify_team_channel
        await notify_team_channel(employee_name=name, department=department)
    except Exception as e:
        logger.debug(f"Slack employee.created notification failed: {e}")


def bind_event_notifications():
    bus = get_event_bus()
    for event_type in NOTIFICATION_TEMPLATES:
        bus.subscribe(event_type, lambda tid, pl, et=event_type: _handle_hr_event(tid, pl, et))

    bus.subscribe("vacation.approved", _slack_vacation_approved)
    bus.subscribe("kudos.received", _slack_kudos_received)
    bus.subscribe("employee.created", _slack_employee_created)
