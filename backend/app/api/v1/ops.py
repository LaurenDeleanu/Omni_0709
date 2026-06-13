from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from app.api.dependencies import get_tenant_db, get_current_user
from app.models.ops import FacilityAsset, AssetBooking, VisitorLog, MaintenanceRequest
from app.schemas.ops import (
    FacilityAssetCreate, FacilityAssetResponse,
    AssetBookingCreate, AssetBookingResponse,
    VisitorLogCreate, VisitorLogUpdate, VisitorLogResponse,
    CalendarBookingResponse,
    MaintenanceRequestCreate, MaintenanceRequestUpdate, MaintenanceRequestResponse,
    MaintenanceStats
)

router = APIRouter()

# --- Assets ---

@router.get("/assets", response_model=List[FacilityAssetResponse])
async def get_assets(type: str = None, db: AsyncSession = Depends(get_tenant_db)):
    query = select(FacilityAsset)
    if type:
        query = query.where(FacilityAsset.type == type)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/assets", response_model=FacilityAssetResponse)
async def create_asset(data: FacilityAssetCreate, db: AsyncSession = Depends(get_tenant_db)):
    db_asset = FacilityAsset(**data.model_dump())
    db.add(db_asset)
    await db.commit()
    await db.refresh(db_asset)
    return db_asset

# --- Bookings ---

@router.get("/bookings", response_model=List[AssetBookingResponse])
async def get_bookings(employee_id: str = None, db: AsyncSession = Depends(get_tenant_db)):
    query = select(AssetBooking)
    if employee_id:
        query = query.where(AssetBooking.employee_id == employee_id)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/bookings", response_model=AssetBookingResponse)
async def create_booking(data: AssetBookingCreate, db: AsyncSession = Depends(get_tenant_db)):
    # Check for overlapping bookings
    overlapping = await db.execute(
        select(AssetBooking).where(
            and_(
                AssetBooking.asset_id == data.asset_id,
                AssetBooking.status == "confirmed",
                AssetBooking.start_time < data.end_time,
                AssetBooking.end_time > data.start_time
            )
        )
    )
    if overlapping.scalars().first():
        raise HTTPException(status_code=400, detail="The asset is already booked for this time period.")
        
    db_booking = AssetBooking(**data.model_dump())
    db.add(db_booking)
    await db.commit()
    await db.refresh(db_booking)

    try:
        from app.services.notification_utils import create_and_push_notification
        asset_result = await db.execute(select(FacilityAsset).where(FacilityAsset.id == data.asset_id))
        asset = asset_result.scalar_one_or_none()
        asset_name = asset.name if asset else "Resource"
        await create_and_push_notification(
            db,
            user_id=data.employee_id,
            title="Booking Confirmed",
            message=f"Your booking for '{asset_name}' from {data.start_time} to {data.end_time} has been confirmed",
            type_="system",
            link="/dashboard/ops?tab=bookings",
        )
        await db.commit()
    except Exception:
        pass

    return db_booking

# --- Visitors ---

@router.get("/visitors", response_model=List[VisitorLogResponse])
async def get_visitors(host_id: str = None, db: AsyncSession = Depends(get_tenant_db)):
    query = select(VisitorLog).order_by(VisitorLog.expected_arrival.asc())
    if host_id:
        query = query.where(VisitorLog.host_id == host_id)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/visitors", response_model=VisitorLogResponse)
async def create_visitor(data: VisitorLogCreate, db: AsyncSession = Depends(get_tenant_db)):
    db_visitor = VisitorLog(**data.model_dump())
    db.add(db_visitor)
    await db.commit()
    await db.refresh(db_visitor)
    return db_visitor

@router.put("/visitors/{visitor_id}", response_model=VisitorLogResponse)
async def update_visitor(visitor_id: str, data: VisitorLogUpdate, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(VisitorLog).where(VisitorLog.id == visitor_id))
    visitor = result.scalars().first()
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
        
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(visitor, key, value)
        
    # Auto-assign timestamps based on status if not explicitly provided
    was_checked_in = visitor.status == "checked_in" or (visitor.check_in_time is not None)
    if data.status == "checked_in" and not data.check_in_time and not visitor.check_in_time:
        visitor.check_in_time = datetime.now(timezone.utc)
    elif data.status == "checked_out" and not data.check_out_time and not visitor.check_out_time:
        visitor.check_out_time = datetime.now(timezone.utc)
        
    await db.commit()
    await db.refresh(visitor)

    if visitor.status == "checked_in" and not was_checked_in and visitor.host_id:
        try:
            from app.services.notification_utils import create_and_push_notification
            await create_and_push_notification(
                db,
                user_id=visitor.host_id,
                title="Visitor Checked In",
                message=f"{visitor.visitor_name} from {visitor.company or 'Unknown'} has arrived",
                type_="system",
                link="/dashboard/ops?tab=visitors",
            )
            await db.commit()
        except Exception:
            pass

    return visitor

@router.put("/visitors/{visitor_id}/check-out", response_model=VisitorLogResponse)
async def check_out_visitor(visitor_id: str, db: AsyncSession = Depends(get_tenant_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(VisitorLog).where(VisitorLog.id == visitor_id))
    visitor = result.scalars().first()
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    visitor.check_out_time = datetime.now(timezone.utc)
    visitor.status = "checked_out"
    await db.commit()
    await db.refresh(visitor)
    return visitor

@router.get("/bookings/calendar", response_model=List[CalendarBookingResponse])
async def get_calendar_bookings(
    start: str = Query(...),
    end: str = Query(...),
    asset_type: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    current_user=Depends(get_current_user)
):
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end) + timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD)")

    query = select(
        AssetBooking.id,
        AssetBooking.asset_id,
        AssetBooking.start_time,
        AssetBooking.end_time,
        AssetBooking.status,
        AssetBooking.employee_id,
        FacilityAsset.name.label("asset_name"),
        FacilityAsset.type.label("asset_type"),
    ).join(FacilityAsset, AssetBooking.asset_id == FacilityAsset.id).where(
        and_(
            AssetBooking.start_time < end_dt,
            AssetBooking.end_time > start_dt
        )
    )

    if asset_type:
        query = query.where(FacilityAsset.type == asset_type)

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": row.id,
            "asset_id": row.asset_id,
            "asset_name": row.asset_name,
            "asset_type": row.asset_type,
            "employee_name": row.employee_id,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "status": row.status,
        }
        for row in rows
    ]

@router.get("/maintenance", response_model=List[MaintenanceRequestResponse])
async def get_maintenance_requests(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    current_user=Depends(get_current_user)
):
    query = select(MaintenanceRequest).order_by(MaintenanceRequest.created_at.desc())
    if status:
        query = query.where(MaintenanceRequest.status == status)
    if priority:
        query = query.where(MaintenanceRequest.priority == priority)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/maintenance", response_model=MaintenanceRequestResponse)
async def create_maintenance_request(
    data: MaintenanceRequestCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user=Depends(get_current_user)
):
    db_request = MaintenanceRequest(**data.model_dump())
    db.add(db_request)
    await db.commit()
    await db.refresh(db_request)

    try:
        from app.services.notification_utils import create_and_push_notification
        involved = set()
        if data.reported_by_id:
            involved.add(data.reported_by_id)
        for uid in involved:
            await create_and_push_notification(
                db,
                user_id=uid,
                title=f"Maintenance Created: {data.title}",
                message=f"New maintenance request '{data.title}' has been created (priority: {data.priority})",
                type_="task",
                link="/dashboard/ops?tab=maintenance",
            )
        await db.commit()
    except Exception:
        pass

    return db_request

@router.put("/maintenance/{request_id}", response_model=MaintenanceRequestResponse)
async def update_maintenance_request(
    request_id: str,
    data: MaintenanceRequestUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(select(MaintenanceRequest).where(MaintenanceRequest.id == request_id))
    request = result.scalars().first()
    if not request:
        raise HTTPException(status_code=404, detail="Maintenance request not found")

    update_data = data.model_dump(exclude_unset=True)
    previous_status = request.status
    for key, value in update_data.items():
        setattr(request, key, value)

    if data.status == "resolved" and not request.resolved_at:
        request.resolved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(request)

    if request.status == "resolved" and previous_status != "resolved":
        try:
            from app.services.notification_utils import create_and_push_notification
            involved = set()
            if request.reported_by_id:
                involved.add(request.reported_by_id)
            if request.assigned_to_id:
                involved.add(request.assigned_to_id)
            for uid in involved:
                await create_and_push_notification(
                    db,
                    user_id=uid,
                    title=f"Maintenance Resolved: {request.title}",
                    message=f"Maintenance request '{request.title}' has been marked as resolved",
                    type_="system",
                    link="/dashboard/ops?tab=maintenance",
                )
            await db.commit()
        except Exception:
            pass

    return request

@router.get("/maintenance/stats", response_model=MaintenanceStats)
async def get_maintenance_stats(
    db: AsyncSession = Depends(get_tenant_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(select(MaintenanceRequest))
    all_requests = result.scalars().all()

    def count_by_status(s): return sum(1 for r in all_requests if r.status == s)
    def count_by_priority(p): return sum(1 for r in all_requests if r.priority == p)

    return MaintenanceStats(
        total=len(all_requests),
        reported=count_by_status("reported"),
        in_progress=count_by_status("in_progress"),
        resolved=count_by_status("resolved"),
        closed=count_by_status("closed"),
        low=count_by_priority("low"),
        medium=count_by_priority("medium"),
        high=count_by_priority("high"),
        critical=count_by_priority("critical"),
    )
