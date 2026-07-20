import json
import logging
import httpx
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("successcore.slack")

SLACK_WEBHOOK_URLS: dict = {}


def configure_slack(tenant_id: str, webhook_url: str):
    SLACK_WEBHOOK_URLS[tenant_id] = webhook_url


async def send_slack_notification(
    tenant_id: str,
    message: str,
    title: Optional[str] = None,
    color: str = "#36a64f",
) -> bool:
    webhook_url = SLACK_WEBHOOK_URLS.get(tenant_id)
    if not webhook_url:
        webhook_url = SLACK_WEBHOOK_URLS.get("*")
    if not webhook_url:
        return False

    payload = {
        "attachments": [
            {
                "color": color,
                "title": title or "SuccessCore Notification",
                "text": message,
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code == 200:
                return True
            logger.warning(f"Slack webhook returned {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Slack notification failed: {e}")
        return False


async def send_slack_message(channel: str, text: str, blocks: list = None) -> bool:
    bot_token = settings.SLACK_BOT_TOKEN
    if not bot_token:
        logger.warning("SLACK_BOT_TOKEN not configured")
        return False

    body = {"channel": channel, "text": text}
    if blocks:
        body["blocks"] = blocks

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                json=body,
                headers={"Authorization": f"Bearer {bot_token}"},
            )
            data = resp.json()
            if data.get("ok"):
                return True
            logger.warning(f"Slack chat.postMessage failed: {data.get('error', 'unknown')}")
            return False
    except Exception as e:
        logger.error(f"Slack send_slack_message failed: {e}")
        return False


async def notify_vacation_approved(user_email: str, start_date: str, end_date: str) -> bool:
    text = f"*Vacation Approved!*\n*Dates:* {start_date} → {end_date}"
    return await send_slack_message(
        channel=f"@{user_email}",
        text=text,
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": "*✈️ Vacation Approved*"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Start:* {start_date}"},
                {"type": "mrkdwn", "text": f"*End:* {end_date}"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn", "text": "Enjoy your time off! 🎉"}},
        ],
    )


async def notify_kudos_received(receiver_email: str, sender_name: str, badge: str, message: str) -> bool:
    return await send_slack_message(
        channel=f"@{receiver_email}",
        text=f"🎉 {sender_name} gave you a Kudos: {message}",
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": "🎉 *You received a Kudos!*"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*From:* {sender_name}"},
                {"type": "mrkdwn", "text": f"*Badge:* {badge}"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"_{message}_"}},
        ],
    )


async def notify_team_channel(employee_name: str, department: str) -> bool:
    return await send_slack_message(
        channel="#general",
        text=f"👋 Welcome *{employee_name}* to the team! ({department or 'N/A'})",
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": f"👋 *New team member!* {employee_name} has joined {department or 'the team'} 🎉"}},
        ],
    )


EVENT_MESSAGES = {
    "employee.created": "New employee **{name}** has joined the team.",
    "vacation.approved": "Vacation for **{name}** has been approved ({start} to {end}).",
    "expense.approved": "Expense claim **{amount}** by {name} was approved.",
    "course.completed": "**{name}** completed course: {title}.",
    "kudos.received": "**{sender}** gave kudos to **{receiver}**: {message}",
}


async def dispatch_slack_event(tenant_id: str, event_type: str, data: dict) -> bool:
    template = EVENT_MESSAGES.get(event_type)
    if not template:
        return False
    try:
        message = template.format(**data)
    except KeyError:
        message = f"Event: {event_type} — {json.dumps(data)}"
    return await send_slack_notification(tenant_id, message, title=f"HR Event: {event_type}")
