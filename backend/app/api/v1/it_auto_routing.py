from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import Optional
from pydantic import BaseModel

from app.api.dependencies import get_tenant_db, require_roles
from app.models.it import ITTicket
from app.models.user import User

router = APIRouter()


class AutoRouteRequest(BaseModel):
    ticket_id: str
    strategy: str = "round_robin"


class RouteResult(BaseModel):
    ticket_id: str
    assigned_to: Optional[str] = None
    assignee_name: Optional[str] = None
    strategy: str


@router.post("/it/tickets/{ticket_id}/auto-assign", response_model=RouteResult)
async def auto_assign_ticket(
    ticket_id: str,
    strategy: str = "round_robin",
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin", "it_manager"]))
):
    ticket_result = await db.execute(select(ITTicket).where(ITTicket.id == ticket_id))
    ticket = ticket_result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    category = getattr(ticket, "category", "general")
    priority = getattr(ticket, "priority", "medium")

    it_roles = ["it_manager", "hr_admin", "sys_admin"]
    users_result = await db.execute(
        select(User).where(User.role.in_(it_roles), User.is_active == True)
    )
    it_staff = users_result.scalars().all()

    if not it_staff:
        return RouteResult(ticket_id=ticket_id, assigned_to=None, assignee_name=None, strategy=strategy)

    workload = {}
    for user in it_staff:
        count = await db.scalar(
            select(func.count()).select_from(ITTicket).where(
                ITTicket.assignee_id == user.id,
                ITTicket.status.in_(["open", "in_progress"])
            )
        )
        workload[user.id] = count or 0

    if strategy == "round_robin":
        sorted_staff = sorted(it_staff, key=lambda u: workload[u.id])
        assignee = sorted_staff[0]
    elif strategy == "least_busy":
        sorted_staff = sorted(it_staff, key=lambda u: workload[u.id])
        assignee = sorted_staff[0]
    elif strategy == "skill_based":
        skills_map = {
            "hardware": lambda u: u.role == "it_manager" or u.department == "IT",
            "software": lambda u: u.role == "it_manager" or u.department == "IT",
            "network": lambda u: u.role == "it_manager",
            "general": lambda u: True,
        }
        matcher = skills_map.get(category, lambda u: True)
        matching = [u for u in it_staff if matcher(u)]
        if not matching:
            matching = it_staff
        sorted_staff = sorted(matching, key=lambda u: workload.get(u.id, 0))
        assignee = sorted_staff[0]
    else:
        sorted_staff = sorted(it_staff, key=lambda u: workload[u.id])
        assignee = sorted_staff[0]

    setattr(ticket, "assignee_id", assignee.id)
    if hasattr(ticket, "status") and getattr(ticket, "status") == "open":
        setattr(ticket, "status", "in_progress")

    await db.commit()

    return RouteResult(
        ticket_id=ticket_id,
        assigned_to=assignee.id,
        assignee_name=assignee.full_name or assignee.email,
        strategy=strategy,
    )


@router.post("/it/tickets/auto-assign-all", response_model=dict)
async def auto_assign_all_unassigned(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin", "it_manager"]))
):
    result = await db.execute(
        select(ITTicket).where(
            (ITTicket.assignee_id == None) | (ITTicket.assignee_id == ""),
            ITTicket.status.in_(["open"]),
        )
    )
    unassigned = result.scalars().all()

    it_roles = ["it_manager", "hr_admin", "sys_admin"]
    users_result = await db.execute(
        select(User).where(User.role.in_(it_roles), User.is_active == True)
    )
    it_staff = users_result.scalars().all()

    if not it_staff or not unassigned:
        return {"assigned": 0, "total": len(unassigned), "message": "No staff or no unassigned tickets"}

    assigns = 0
    for i, ticket in enumerate(unassigned):
        assignee = it_staff[i % len(it_staff)]
        setattr(ticket, "assignee_id", assignee.id)
        if getattr(ticket, "status") == "open":
            setattr(ticket, "status", "in_progress")
        assigns += 1

    await db.commit()
    return {"assigned": assigns, "total": len(unassigned), "message": f"{assigns} tickets auto-assigned successfully"}


@router.get("/it/assignment-status", response_model=dict)
async def get_assignment_status(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin", "it_manager"]))
):
    total = await db.scalar(select(func.count()).select_from(ITTicket))
    unassigned = await db.scalar(
        select(func.count()).select_from(ITTicket).where(
            (ITTicket.assignee_id == None) | (ITTicket.assignee_id == "")
        )
    )
    open_tickets = await db.scalar(
        select(func.count()).select_from(ITTicket).where(ITTicket.status.in_(["open"]))
    )

    it_roles = ["it_manager", "hr_admin", "sys_admin"]
    users_result = await db.execute(
        select(User.id, User.full_name, User.email).where(User.role.in_(it_roles), User.is_active == True)
    )
    staff = users_result.all()

    workload = []
    for uid, name, email in staff:
        count = await db.scalar(
            select(func.count()).select_from(ITTicket).where(
                ITTicket.assignee_id == uid, ITTicket.status.in_(["open", "in_progress"])
            )
        )
        workload.append({"user_id": uid, "name": name or email, "active_tickets": count or 0})

    return {
        "total_tickets": total or 0,
        "open_tickets": open_tickets or 0,
        "unassigned": unassigned or 0,
        "available_agents": len(staff),
        "agent_workload": workload,
    }
