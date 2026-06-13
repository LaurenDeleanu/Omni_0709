import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("successcore.email_sequences")

EMAIL_TEMPLATES = {
    "welcome": {
        "subject": "Welcome to {{company_name}}!",
        "delay_hours": 0,
        "body": "Hi {{first_name}},\n\nWelcome aboard! We're excited to have you on the team.\n\nYour first day is {{start_date}}. Here's what you need to know:\n- Your buddy is {{buddy_name}}\n- Check your email for account setup instructions\n\nBest,\n{{company_name}} HR",
    },
    "follow_up_3d": {
        "subject": "Checking in - how's it going?",
        "delay_hours": 72,
        "body": "Hi {{first_name}},\n\nJust checking in to see how your first few days are going.\n\nIs there anything you need help with? Don't hesitate to reach out.\n\nBest,\n{{sender_name}}",
    },
    "demo_reminder": {
        "subject": "Reminder: Your demo is tomorrow",
        "delay_hours": 24,
        "body": "Hi {{first_name}},\n\nQuick reminder that your product demo is scheduled for {{demo_time}}.\n\nJoin here: {{demo_link}}\n\nLooking forward to it!\n{{sender_name}}",
    },
    "nurture_weekly": {
        "subject": "Resources to help you get started",
        "delay_hours": 168,
        "body": "Hi {{first_name}},\n\nHere are some resources that might interest you:\n- {{resource_1}}\n- {{resource_2}}\n- {{resource_3}}\n\nLet me know if you have any questions.\n\nBest,\n{{sender_name}}",
    },
    "reengagement": {
        "subject": "We miss you at {{company_name}}",
        "delay_hours": 720,
        "body": "Hi {{first_name}},\n\nIt's been a while! We wanted to check in and see if you're still interested in {{company_name}}.\n\nHere's what's new: {{whats_new}}\n\nWould you like to reconnect?\n\nBest,\n{{sender_name}}",
    },
}

SEQUENCE_TEMPLATES = {
    "onboarding": {
        "name": "Employee Onboarding",
        "emails": [
            {"template": "welcome", "delay_hours": 0},
            {"template": "follow_up_3d", "delay_hours": 72},
        ],
    },
    "sales_nurture": {
        "name": "Sales Lead Nurture",
        "emails": [
            {"template": "demo_reminder", "delay_hours": 24},
            {"template": "nurture_weekly", "delay_hours": 168},
            {"template": "reengagement", "delay_hours": 720},
        ],
    },
}


def get_sequence(sequence_id: str) -> Optional[Dict[str, Any]]:
    return SEQUENCE_TEMPLATES.get(sequence_id)


def list_sequences() -> List[Dict[str, Any]]:
    return [
        {"id": seq_id, "name": seq["name"], "email_count": len(seq["emails"])}
        for seq_id, seq in SEQUENCE_TEMPLATES.items()
    ]


def list_templates() -> List[Dict[str, Any]]:
    return [
        {"id": tid, "subject": t["subject"], "delay_hours": t["delay_hours"]}
        for tid, t in EMAIL_TEMPLATES.items()
    ]


def render_template(template_id: str, variables: Dict[str, str]) -> Dict[str, str]:
    template = EMAIL_TEMPLATES.get(template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")

    subject = template["subject"]
    body = template["body"]
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        if placeholder in subject:
            subject = subject.replace(placeholder, value)
        if placeholder in body:
            body = body.replace(placeholder, value)

    return {"subject": subject, "body": body, "delay_hours": template["delay_hours"]}


async def schedule_sequence(
    db: AsyncSession,
    sequence_id: str,
    contact_email: str,
    variables: Dict[str, str],
    start_at: Optional[str] = None,
) -> Dict[str, Any]:
    sequence = get_sequence(sequence_id)
    if not sequence:
        raise ValueError(f"Sequence {sequence_id} not found")

    scheduled = []
    base_time = datetime.fromisoformat(start_at) if start_at else datetime.now(timezone.utc)

    for email_step in sequence["emails"]:
        send_time = base_time + timedelta(hours=email_step["delay_hours"])
        rendered = render_template(email_step["template"], variables)
        scheduled.append({
            "id": uuid.uuid4().hex,
            "template_id": email_step["template"],
            "subject": rendered["subject"],
            "to": contact_email,
            "send_at": send_time.isoformat(),
            "delay_hours": email_step["delay_hours"],
        })

    logger.info(f"Email sequence '{sequence_id}' scheduled: {len(scheduled)} emails to {contact_email}")
    return {
        "sequence_id": sequence_id,
        "recipient": contact_email,
        "total_emails": len(scheduled),
        "emails": scheduled,
    }
