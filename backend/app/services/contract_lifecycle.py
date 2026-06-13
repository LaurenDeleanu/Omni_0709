import logging
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.legal import Contract
from app.services.email_service import send_email
from app.services.notification_utils import create_and_push_notification

logger = logging.getLogger("successcore.contract_lifecycle")

EXPIRY_WINDOW_DAYS = 30


async def check_expiring_contracts(db: AsyncSession) -> list:
    cutoff = datetime.now(timezone.utc) + timedelta(days=EXPIRY_WINDOW_DAYS)
    result = await db.execute(
        select(Contract)
        .where(
            Contract.status == "active",
            Contract.valid_until.isnot(None),
            Contract.valid_until <= cutoff,
            Contract.valid_until > func.now(),
        )
        .order_by(Contract.valid_until.asc())
    )
    contracts = result.scalars().all()
    logger.info(f"Found {len(contracts)} contracts expiring within {EXPIRY_WINDOW_DAYS} days")
    return contracts


async def send_expiry_alerts(db: AsyncSession) -> dict:
    contracts = await check_expiring_contracts(db)
    if not contracts:
        return {"sent": 0, "contracts": []}

    alerts_sent = []
    for contract in contracts:
        days_left = (contract.valid_until - datetime.now(timezone.utc)).days
        cid = contract.id if isinstance(contract.id, str) else str(contract.id)

        await create_and_push_notification(
            db=db,
            user_id="admin",
            title=f"Contract Expiring: {contract.title}",
            message=f"Contract '{contract.title}' with {contract.party_name} expires in {days_left} days ({contract.valid_until.date()}).",
            type_="contract_expiry",
        )

        await send_email(
            to="hr_admin@acme.corp",
            subject=f"[Contract Expiry] {contract.title} — {days_left} days remaining",
            body=(
                f"<h3>Contract Expiry Alert</h3>"
                f"<p><strong>Contract:</strong> {contract.title}</p>"
                f"<p><strong>Party:</strong> {contract.party_name}</p>"
                f"<p><strong>Expires:</strong> {contract.valid_until.date()}</p>"
                f"<p><strong>Days remaining:</strong> {days_left}</p>"
            ),
            html=True,
        )

        alerts_sent.append({
            "contract_id": cid,
            "title": contract.title,
            "party_name": contract.party_name,
            "expires": contract.valid_until.isoformat(),
            "days_left": days_left,
        })

    return {"sent": len(alerts_sent), "contracts": alerts_sent}


async def renew_contract(contract_id: str, new_end_date: str, db: AsyncSession) -> dict:
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    original = result.scalar_one_or_none()
    if not original:
        raise ValueError(f"Contract {contract_id} not found")

    new_id = uuid.uuid4().hex
    new_start = datetime.now(timezone.utc)
    new_end = datetime.fromisoformat(new_end_date)

    renewed = Contract(
        id=new_id,
        title=original.title,
        description=original.description,
        party_name=original.party_name,
        status="active",
        valid_from=new_start,
        valid_until=new_end,
        document_url=original.document_url,
    )
    db.add(renewed)

    original.status = "expired"
    await db.commit()
    await db.refresh(renewed)

    logger.info(f"Contract {contract_id} renewed as {new_id} (expires {new_end_date})")
    return {
        "id": renewed.id,
        "title": renewed.title,
        "status": renewed.status,
        "valid_from": renewed.valid_from.isoformat() if renewed.valid_from else None,
        "valid_until": renewed.valid_until.isoformat() if renewed.valid_until else None,
        "original_status": original.status,
    }


async def get_contract_timeline(contract_id: str, db: AsyncSession) -> list:
    from app.models.legal import WhistleblowerReport

    timeline = []

    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        return []

    timeline.append({
        "event": "contract_created",
        "timestamp": contract.created_at.isoformat() if contract.created_at else None,
        "details": f"Contract '{contract.title}' created with {contract.party_name}",
    })

    if contract.valid_from:
        timeline.append({
            "event": "contract_active",
            "timestamp": contract.valid_from.isoformat(),
            "details": f"Contract became active",
        })

    if contract.status == "expired" and contract.valid_until:
        timeline.append({
            "event": "contract_expired",
            "timestamp": contract.valid_until.isoformat(),
            "details": f"Contract expired",
        })

    timeline.sort(key=lambda e: e["timestamp"] or "")
    return timeline


async def get_contract_stats(tenant_id: str, db: AsyncSession) -> dict:
    result = await db.execute(
        select(
            Contract.status,
            func.count(Contract.id).label("count"),
        ).group_by(Contract.status)
    )
    rows = result.all()

    stats = {"active": 0, "draft": 0, "pending_signature": 0, "expired": 0, "expiring_soon": 0, "total": 0}
    for status, count in rows:
        stats[status] = count
        stats["total"] += count

    cutoff = datetime.now(timezone.utc) + timedelta(days=EXPIRY_WINDOW_DAYS)
    expiring_result = await db.execute(
        select(func.count(Contract.id))
        .where(
            Contract.status == "active",
            Contract.valid_until.isnot(None),
            Contract.valid_until <= cutoff,
            Contract.valid_until > func.now(),
        )
    )
    stats["expiring_soon"] = expiring_result.scalar() or 0

    return stats
