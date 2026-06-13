import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

logger = logging.getLogger("successcore.it_assets")


HARDWARE_CATEGORIES = ["laptop", "desktop", "monitor", "keyboard", "mouse", "phone", "tablet", "printer", "router", "server", "other"]
SOFTWARE_LICENSES = ["microsoft_365", "google_workspace", "slack", "notion", "jira", "figma", "adobe_cc", "zoom", "vpn", "other"]


async def register_asset(
    db: AsyncSession,
    name: str,
    category: str = "other",
    asset_type: str = "hardware",
    serial_number: str = "",
    assigned_to: Optional[str] = None,
    status: str = "available",
    purchase_date: Optional[str] = None,
    warranty_expiry: Optional[str] = None,
    notes: str = "",
    value: float = 0,
) -> Dict[str, Any]:
    asset_id = uuid.uuid4().hex

    asset = {
        "id": asset_id,
        "name": name,
        "category": category,
        "asset_type": asset_type,
        "serial_number": serial_number,
        "assigned_to": assigned_to,
        "status": status,
        "purchase_date": purchase_date,
        "warranty_expiry": warranty_expiry,
        "notes": notes,
        "value": value,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        from app.models.it import ITAsset
        db_asset = ITAsset(
            id=asset_id,
            name=name, category=category, asset_type=asset_type,
            serial_number=serial_number, assigned_to=assigned_to,
            status=status, notes=notes, value=value,
        )
        if purchase_date:
            db_asset.purchase_date = datetime.fromisoformat(purchase_date)
        if warranty_expiry:
            db_asset.warranty_expiry = datetime.fromisoformat(warranty_expiry)
        db.add(db_asset)
        await db.commit()
    except Exception as e:
        logger.warning(f"IT asset DB storage skipped: {e}")

    logger.info(f"IT asset registered: {name} ({asset_id[:8]})")
    return asset


async def assign_asset(db: AsyncSession, asset_id: str, user_id: str) -> Dict[str, Any]:
    try:
        from app.models.it import ITAsset
        asset = await db.get(ITAsset, asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        asset.assigned_to = user_id
        asset.status = "assigned"
        await db.commit()
        return {"asset_id": asset_id, "assigned_to": user_id, "status": "assigned"}
    except Exception:
        return {"asset_id": asset_id, "assigned_to": user_id, "status": "assigned"}


async def list_assets(
    db: AsyncSession,
    category: str = "",
    asset_type: str = "",
    status: str = "",
    assigned_to: str = "",
    limit: int = 100,
) -> List[Dict[str, Any]]:
    try:
        from app.models.it import ITAsset
        query = select(ITAsset)
        if category:
            query = query.where(ITAsset.category == category)
        if status:
            query = query.where(ITAsset.status == status)
        if assigned_to:
            query = query.where(ITAsset.assigned_to == assigned_to)
        result = await db.execute(query.order_by(ITAsset.created_at.desc()).limit(limit))
        assets = result.scalars().all()
        return [
            {"id": a.id, "name": a.name, "category": a.category, "status": a.status,
             "assigned_to": a.assigned_to, "serial_number": getattr(a, "serial_number", ""), "value": getattr(a, "value", 0)}
            for a in assets
        ]
    except Exception:
        return []


async def get_asset_summary(db: AsyncSession) -> Dict[str, Any]:
    assets = await list_assets(db, limit=500)

    total = len(assets)
    assigned = sum(1 for a in assets if a["assigned_to"])
    available = sum(1 for a in assets if a["status"] == "available")
    maintenance = sum(1 for a in assets if a["status"] == "maintenance")

    by_category: Dict[str, int] = {}
    for a in assets:
        cat = a.get("category", "other")
        by_category[cat] = by_category.get(cat, 0) + 1

    by_status: Dict[str, int] = {}
    for a in assets:
        st = a.get("status", "available")
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "total_assets": total,
        "assigned_count": assigned,
        "available_count": available,
        "maintenance_count": maintenance,
        "by_category": by_category,
        "by_status": by_status,
    }


async def get_warranty_alerts(db: AsyncSession, within_days: int = 30) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=within_days)

    try:
        from app.models.it import ITAsset
        result = await db.execute(
            select(ITAsset).where(
                and_(ITAsset.warranty_expiry != None, ITAsset.warranty_expiry <= cutoff)
            )
        )
        assets = result.scalars().all()
        from datetime import timedelta
        return [
            {
                "id": a.id, "name": a.name,
                "warranty_expiry": a.warranty_expiry.isoformat() if a.warranty_expiry else "",
                "days_remaining": (a.warranty_expiry - now).days if a.warranty_expiry else 0,
            }
            for a in assets
        ]
    except Exception:
        return []
