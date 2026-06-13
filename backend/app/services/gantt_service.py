import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

logger = logging.getLogger("successcore.gantt")


async def get_project_timeline(
    db: AsyncSession,
    project_id: Optional[str] = None,
    user_id: str = "",
) -> Dict[str, Any]:
    tasks = []
    dependencies = []
    milestones = []

    try:
        from app.models.work import Project, Task
        query = select(Project)
        if project_id:
            query = query.where(Project.id == project_id)
        if user_id:
            query = query.where(Project.owner_id == user_id)
        result = await db.execute(query.order_by(Project.created_at.desc()).limit(10))
        projects = result.scalars().all()

        for project in projects:
            tasks_res = await db.execute(
                select(Task).where(Task.project_id == project.id).order_by(Task.order)
            )
            project_tasks = tasks_res.scalars().all()

            for i, task in enumerate(project_tasks):
                start = task.start_date.isoformat() if getattr(task, "start_date", None) else datetime.now(timezone.utc).isoformat()
                end = task.end_date.isoformat() if getattr(task, "end_date", None) else (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
                deps = getattr(task, "dependency_ids", []) or []
                for dep_id in deps:
                    dependencies.append({"from": dep_id, "to": task.id})

                tasks.append({
                    "id": task.id,
                    "project_id": project.id,
                    "name": getattr(task, "title", task.id),
                    "start": start.split("T")[0] if "T" in start else start,
                    "end": end.split("T")[0] if "T" in end else end,
                    "progress": getattr(task, "progress_pct", 0) or 0,
                    "status": getattr(task, "status", "todo"),
                    "assignee": getattr(task, "assignee_id", ""),
                    "parent": project.id if i == 0 else None,
                    "dependencies": deps,
                })

            milestones.append({
                "id": project.id,
                "name": getattr(project, "name", project.id),
                "start": tasks[-1]["start"] if tasks else datetime.now(timezone.utc).date().isoformat(),
                "end": tasks[-1]["end"] if tasks else "",
                "progress": int(sum(t["progress"] for t in tasks) / max(len(tasks), 1)),
                "task_count": len(project_tasks),
            })
    except Exception as e:
        logger.warning(f"Gantt data query failed, using empty data: {e}")

    return {
        "tasks": tasks,
        "dependencies": dependencies,
        "milestones": milestones,
        "total_tasks": len(tasks),
        "total_projects": len(set(t.get("project_id", "") for t in tasks if t.get("project_id"))),
    }


async def get_team_workload_gantt(
    db: AsyncSession,
    team_id: str = "",
    days_ahead: int = 30,
) -> Dict[str, Any]:
    members = {}
    try:
        from app.models.work import Task
        from app.models.user import User

        start = datetime.now(timezone.utc)
        end = start + timedelta(days=days_ahead)

        tasks_res = await db.execute(
            select(Task).where(
                and_(Task.start_date <= end, Task.end_date >= start)
            ).order_by(Task.start_date)
        )
        tasks = tasks_res.scalars().all()

        for task in tasks:
            assignee = getattr(task, "assignee_id", "unassigned")
            if assignee not in members:
                members[assignee] = {"assignee": assignee, "tasks": [], "total_hours": 0}

            member = members[assignee]
            member["tasks"].append({
                "id": task.id,
                "name": getattr(task, "title", task.id),
                "status": getattr(task, "status", "todo"),
                "start": task.start_date.date().isoformat() if task.start_date else start.date().isoformat(),
                "end": task.end_date.date().isoformat() if task.end_date else (start + timedelta(days=2)).date().isoformat(),
                "progress": getattr(task, "progress_pct", 0) or 0,
                "priority": getattr(task, "priority", "medium"),
            })

            if task.start_date and task.end_date:
                member["total_hours"] += (task.end_date - task.start_date).total_seconds() / 3600

        if assignee:
            users_res = await db.execute(select(User).where(User.id.in_(members.keys())))
            for user in users_res.scalars().all():
                if user.id in members:
                    members[user.id]["name"] = user.full_name or user.email
                    members[user.id]["email"] = user.email

    except Exception as e:
        logger.warning(f"Team workload query failed: {e}")

    return {
        "period_days": days_ahead,
        "team_members": list(members.values()),
        "total_tasks": sum(len(m["tasks"]) for m in members.values()),
        "total_members": len(members),
    }


def generate_timeline_data(
    tasks: List[Dict[str, Any]],
    start_date: str = "",
    end_date: str = "",
) -> Dict[str, Any]:
    if not tasks:
        return {"lanes": [], "date_range": {"start": "", "end": ""}, "total_tasks": 0}

    min_date = min(t.get("start", "9999") for t in tasks)
    max_date = max(t.get("end", "0000") for t in tasks)

    lanes: Dict[str, List[Dict[str, Any]]] = {}
    for task in tasks:
        project_id = task.get("project_id", "default")
        if project_id not in lanes:
            lanes[project_id] = []
        lanes[project_id].append(task)

    gantt_lanes = []
    for project_id, project_tasks in lanes.items():
        project_tasks.sort(key=lambda t: t.get("start", ""))
        gantt_lanes.append({
            "lane_id": project_id,
            "label": project_id[:16],
            "tasks": project_tasks,
            "task_count": len(project_tasks),
        })

    return {
        "lanes": gantt_lanes,
        "date_range": {"start": min_date, "end": max_date},
        "total_lanes": len(gantt_lanes),
        "total_tasks": len(tasks),
    }
