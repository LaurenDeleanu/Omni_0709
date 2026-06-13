import logging
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger("successcore.ics")

ICS_TEMPLATE = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//SuccessCore//HR Platform//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
{events}
END:VCALENDAR"""

VEVENT_TEMPLATE = """BEGIN:VEVENT
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{summary}
DESCRIPTION:{description}
UID:{uid}
DTSTAMP:{dtstamp}
END:VEVENT"""


def format_ics_date(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def generate_ics(events: List[dict]) -> str:
    event_blocks = []
    for evt in events:
        event_blocks.append(VEVENT_TEMPLATE.format(
            dtstart=format_ics_date(evt["start"]),
            dtend=format_ics_date(evt["end"]),
            summary=evt.get("summary", "Event"),
            description=evt.get("description", ""),
            uid=evt.get("uid", "event@successcore"),
            dtstamp=format_ics_date(datetime.now(timezone.utc)),
        ))
    return ICS_TEMPLATE.format(events="\n".join(event_blocks))
