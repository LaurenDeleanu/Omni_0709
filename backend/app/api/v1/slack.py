import hashlib
import hmac
import json
import logging
import time
from datetime import date, datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_tenant_db
from app.core.config import settings
from app.models.calendar import VacationRequest
from app.models.kudos import Kudos
from app.models.user import User
from app.services.org_chart import build_org_chart
from app.services.event_publisher import publish_kudos_event
from app.services.event_sourcing import publish_event

logger = logging.getLogger("successcore.slack")

router = APIRouter()


def _verify_slack_signature(request: Request, raw_body: bytes, timestamp: str, signature: str) -> bool:
    secret = settings.SLACK_SIGNING_SECRET
    if not secret:
        logger.warning("SLACK_SIGNING_SECRET not configured")
        return True

    if abs(int(time.time()) - int(timestamp)) > 300:
        return False

    sig_basestring = f"v0:{timestamp}:{raw_body.decode('utf-8')}"
    computed = "v0=" + hmac.new(secret.encode("utf-8"), sig_basestring.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


async def _parse_command(text: str) -> tuple[str, str]:
    parts = text.strip().split(" ", 1)
    cmd = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return cmd, args


async def _find_user_by_name(db: AsyncSession, name: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.full_name.ilike(f"%{name}%") | User.email.ilike(f"%{name}%"))
    )
    return result.scalars().first()


async def _find_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


def _slack_blocks(text: str, fields: list = None) -> list:
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": text}}
    ]
    if fields:
        blocks.append({"type": "section", "fields": fields})
    return blocks


def _ephemeral(text: str, blocks: list = None) -> dict:
    if blocks is None:
        blocks = _slack_blocks(text)
    return {
        "response_type": "ephemeral",
        "text": text,
        "blocks": blocks,
    }


async def _handle_pto(db: AsyncSession, args: str, user_id: str) -> dict:
    parts = args.strip().split()
    if len(parts) < 2:
        return _ephemeral("*Usage:* `/pto request YYYY-MM-DD YYYY-MM-DD [reason]`")

    try:
        start_date = date.fromisoformat(parts[0])
        end_date = date.fromisoformat(parts[1])
    except ValueError:
        return _ephemeral("*Invalid date format.* Use YYYY-MM-DD, e.g. `/pto request 2026-07-01 2026-07-10`")

    reason = " ".join(parts[2:]) if len(parts) > 2 else None

    if end_date < start_date:
        return _ephemeral("*End date cannot be before start date.*")

    vacation = VacationRequest(
        id=uuid.uuid4().hex,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status="pending",
    )
    db.add(vacation)

    try:
        from app.services.event_publisher import publish_vacation_requested
        await publish_vacation_requested(db, vacation.id, user_id, start_date, end_date, "acme_corp")
    except Exception:
        pass

    await db.commit()

    return _ephemeral(
        f"*Vacation request submitted!*\n"
        f"*Dates:* {start_date} → {end_date}\n"
        f"*Status:* Pending approval\n"
        f"*Request ID:* `{vacation.id}`"
    )


async def _handle_who_is(db: AsyncSession, args: str) -> dict:
    if not args.strip():
        return _ephemeral("*Usage:* `/who-is [name or email]`")

    user = await _find_user_by_name(db, args.strip())
    if not user:
        return _ephemeral(f"*No employee found matching:* {args.strip()}")

    fields = [
        {"type": "mrkdwn", "text": f"*Name:* {user.full_name or 'N/A'}"},
        {"type": "mrkdwn", "text": f"*Email:* {user.email}"},
        {"type": "mrkdwn", "text": f"*Department:* {user.department or 'N/A'}"},
        {"type": "mrkdwn", "text": f"*Role:* {user.role or 'N/A'}"},
        {"type": "mrkdwn", "text": f"*Active:* {'Yes' if user.is_active else 'No'}"},
    ]
    return _ephemeral(f"*Employee found:* {user.full_name or user.email}", fields)


async def _handle_org_chart(db: AsyncSession) -> dict:
    chart = await build_org_chart(db)
    total = chart.get("total_employees", 0)
    roots = chart.get("roots", [])

    lines = [f"*Organization Chart*  ({total} employees)", ""]

    def _walk(nodes, indent=0):
        for n in nodes:
            prefix = "  " * indent + ("• " if indent > 0 else "🏢 ")
            lines.append(f"{prefix}*{n['name']}* — _{n.get('role', '')}_ ({n.get('department', '')})")
            _walk(n.get("children", []), indent + 1)

    _walk(roots)
    if not roots:
        lines.append("(No employees found)")

    text = "\n".join(lines)
    return _ephemeral(text[:3000])


async def _handle_kudos(db: AsyncSession, args: str, sender_id: str, sender_name: str) -> dict:
    parts = args.strip().split(" ", 2)
    if len(parts) < 2:
        return _ephemeral("*Usage:* `/kudos @user message`")

    target = parts[0].lstrip("@")
    message = parts[2] if len(parts) > 2 else parts[1] if len(parts) > 1 else ""

    sender_result = await db.execute(select(User).where(User.id == sender_id))
    sender = sender_result.scalar_one_or_none()

    receiver = await _find_user_by_name(db, target)
    if not receiver:
        return _ephemeral(f"*Could not find user:* {target}. Try their full name or email.")

    if sender_id == receiver.id:
        return _ephemeral("*You cannot send Kudos to yourself.*")

    kudos = Kudos(
        id=uuid.uuid4().hex,
        sender_id=sender_id,
        receiver_id=receiver.id,
        message=message,
        badge="Slack Kudos",
    )
    db.add(kudos)

    try:
        await publish_kudos_event(
            db, kudos.id, sender_id, receiver.id, "Slack Kudos", message, "acme_corp"
        )
    except Exception:
        pass

    await db.commit()

    return _ephemeral(
        f"🎉 *Kudos sent!*\n"
        f"*To:* {receiver.full_name or receiver.email}\n"
        f"*Message:* {message}"
    )


async def _handle_status(db: AsyncSession, user_id: str) -> dict:
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return _ephemeral("*Could not find your account.*")

    vac_result = await db.execute(
        select(VacationRequest).where(
            VacationRequest.user_id == user_id,
            VacationRequest.status == "approved",
        )
    )
    approved = vac_result.scalars().all()
    total_days = sum((v.end_date - v.start_date).days + 1 for v in approved)

    vac_result_pending = await db.execute(
        select(VacationRequest).where(
            VacationRequest.user_id == user_id,
            VacationRequest.status == "pending",
        )
    )
    pending = vac_result_pending.scalars().all()
    pending_days = sum((v.end_date - v.start_date).days + 1 for v in pending)

    allowance = getattr(user, "vacation_allowance", 30) or 30
    remaining = allowance - total_days

    fields = [
        {"type": "mrkdwn", "text": f"*Annual Allowance:* {allowance} days"},
        {"type": "mrkdwn", "text": f"*Used (approved):* {total_days} days"},
        {"type": "mrkdwn", "text": f"*Pending:* {pending_days} days"},
        {"type": "mrkdwn", "text": f"*Remaining:* {remaining} days"},
    ]
    return _ephemeral(f"*PTO Status for {user.full_name or user.email}*", fields)


@router.post("/commands")
async def slack_commands(request: Request, db: AsyncSession = Depends(get_tenant_db)):
    raw_body = await request.body()
    try:
        form = await request.form()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid form data")

    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not _verify_slack_signature(request, raw_body, timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    command_text = form.get("text", "")
    user_id = form.get("user_id", "")
    user_name = form.get("user_name", "")
    channel_id = form.get("channel_id", "")
    team_id = form.get("team_id", "")

    cmd, args = await _parse_command(command_text)

    if cmd == "pto":
        return await _handle_pto(db, args, user_id)
    elif cmd == "who-is":
        return await _handle_who_is(db, args)
    elif cmd == "org-chart":
        return await _handle_org_chart(db)
    elif cmd == "kudos":
        return await _handle_kudos(db, args, user_id, user_name)
    elif cmd == "status":
        return await _handle_status(db, user_id)
    else:
        return _ephemeral(
            "*Available commands:*\n"
            "`/pto request YYYY-MM-DD YYYY-MM-DD [reason]` — Request vacation\n"
            "`/who-is [name|email]` — Search employees\n"
            "`/org-chart` — View org chart\n"
            "`/kudos @user message` — Send kudos\n"
            "`/status` — View your PTO balance"
        )


@router.post("/events")
async def slack_events(request: Request, db: AsyncSession = Depends(get_tenant_db)):
    raw_body = await request.body()

    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not _verify_slack_signature(request, raw_body, timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    payload = json.loads(raw_body)

    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}

    if payload.get("type") == "event_callback":
        event = payload.get("event", {})
        event_type = event.get("type", "")

        if event_type == "app_mention":
            text = event.get("text", "")
            channel = event.get("channel", "")
            user = event.get("user", "")

            try:
                from app.services.slack_connector import send_slack_message
                await send_slack_message(
                    channel=channel,
                    text=f"Thanks for the mention <@{user}>! The AI agent is processing: _{text}_",
                )
            except Exception as e:
                logger.error(f"Slack app_mention handler failed: {e}")

    return {"ok": True}
