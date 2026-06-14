from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_, and_, func
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta
import uuid
import os
import shutil
import logging
import json
import asyncio
from pydantic import BaseModel

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import get_tenant_db, get_current_user, require_roles, _get_or_create_sessionmaker
from app.models.user import User
from app.models.chat import Team, TeamMember, ChatRoom, ChatRoomMember, ChatMessage
from app.core.auth import auth_verifier
from app.core.config import settings
from app.api.v1._pagination import paginate_cursor
from app.schemas.pagination import CursorPaginatedResponse
from app.services.agent_runtime import execute_agent_run

logger = logging.getLogger("successcore.chat")

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.get("/ws-token")
async def get_ws_token(current_user: dict = Depends(get_current_user)):
    from jose import jwt
    from datetime import datetime, timezone, timedelta
    from app.core.config import settings
    token = jwt.encode({
        "sub": current_user.get("sub", ""),
        "email": current_user.get("email", ""),
        "tenant_id": current_user.get("https://successcore.com/app_metadata", {}).get("tenant_id", "acme_corp"),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }, settings.SECRET_KEY, algorithm="HS256")
    return {"ws_token": token}

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "uploads")

# --- Pydantic Schemas ---
class RoomResponse(BaseModel):
    id: str
    name: Optional[str] = None
    room_type: str
    department: Optional[str] = None
    team_id: Optional[str] = None
    manager_id: Optional[str] = None
    unread_count: int = 0
    last_message: Optional[str] = None
    last_message_time: Optional[str] = None

class MessageResponse(BaseModel):
    id: str
    room_id: str
    sender_id: str
    sender_name: str
    content: str
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    parent_id: Optional[str] = None
    reactions: dict = {}
    reply_count: int = 0
    created_at: str

class DirectRoomCreate(BaseModel):
    target_user_id: str

class SearchResultResponse(BaseModel):
    id: str
    room_id: str
    room_name: Optional[str] = None
    sender_id: str
    sender_name: str
    content_snippet: str
    created_at: str

class ReactionPayload(BaseModel):
    emoji: str

class ThreadMessageCreate(BaseModel):
    content: str


def _get_user_id(user_payload: dict) -> str:
    sub = user_payload.get("sub", "")
    if "|" in sub:
        return sub.split("|")[-1]
    return sub


async def _auto_provision_rooms(db: AsyncSession, current_user: User):
    """
    Sincroniza y crea las salas de chat automáticas (departamentos, equipos, reportes directos)
    y une al usuario a ellas si aún no es miembro.
    """
    user_id = current_user.id
    
    # 1. Canal de Departamento — unir a TODOS los miembros del depto
    if current_user.department:
        dept = current_user.department
        dept_room_res = await db.execute(
            select(ChatRoom).where(ChatRoom.room_type == "DEPARTMENT", ChatRoom.department == dept)
        )
        dept_room = dept_room_res.scalar_one_or_none()
        if not dept_room:
            dept_room = ChatRoom(id=uuid.uuid4().hex, name=f"Departamento: {dept}", room_type="DEPARTMENT", department=dept)
            db.add(dept_room)
            await db.flush()
            # Unir a TODOS los miembros activos del departamento
            dept_users_res = await db.execute(select(User).where(User.department == dept, User.is_active == True))
            for dept_user in dept_users_res.scalars().all():
                db.add(ChatRoomMember(user_id=dept_user.id, room_id=dept_room.id))
        else:
            # Asegurar que el usuario actual es miembro
            mem_res = await db.execute(select(ChatRoomMember).where(ChatRoomMember.room_id == dept_room.id, ChatRoomMember.user_id == user_id))
            if not mem_res.scalar_one_or_none():
                db.add(ChatRoomMember(user_id=user_id, room_id=dept_room.id))

    # 2. Canales de Equipos (Teams)
    teams_res = await db.execute(
        select(Team).join(TeamMember, TeamMember.team_id == Team.id).where(TeamMember.user_id == user_id)
    )
    teams = teams_res.scalars().all()
    for team in teams:
        team_room_res = await db.execute(
            select(ChatRoom).where(ChatRoom.room_type == "TEAM", ChatRoom.team_id == team.id)
        )
        team_room = team_room_res.scalar_one_or_none()
        if not team_room:
            team_room = ChatRoom(
                id=uuid.uuid4().hex,
                name=f"Equipo: {team.name}",
                room_type="TEAM",
                team_id=team.id
            )
            db.add(team_room)
            await db.flush()
            
        mem_res = await db.execute(
            select(ChatRoomMember).where(ChatRoomMember.room_id == team_room.id, ChatRoomMember.user_id == user_id)
        )
        if not mem_res.scalar_one_or_none():
            db.add(ChatRoomMember(user_id=user_id, room_id=team_room.id))

    # 3. Canales de Jerarquía (Supervisor / Reportes)
    # 3a. Sala del manager — unirse y también unir al manager
    if current_user.manager_id:
        man_res = await db.execute(select(User).where(User.id == current_user.manager_id))
        manager = man_res.scalar_one_or_none()
        if manager:
            man_room_res = await db.execute(select(ChatRoom).where(ChatRoom.room_type == "HIERARCHY", ChatRoom.manager_id == manager.id))
            man_room = man_room_res.scalar_one_or_none()
            if not man_room:
                man_room = ChatRoom(id=uuid.uuid4().hex, name=f"Reportes de {manager.full_name or manager.email}", room_type="HIERARCHY", manager_id=manager.id)
                db.add(man_room)
                await db.flush()
                # Unir al manager
                db.add(ChatRoomMember(user_id=manager.id, room_id=man_room.id))
                # Unir a todos los subordinados del manager
                mgr_reports = await db.execute(select(User).where(User.manager_id == manager.id, User.is_active == True))
                for rep in mgr_reports.scalars().all():
                    db.add(ChatRoomMember(user_id=rep.id, room_id=man_room.id))
            else:
                mem_res = await db.execute(select(ChatRoomMember).where(ChatRoomMember.room_id == man_room.id, ChatRoomMember.user_id == user_id))
                if not mem_res.scalar_one_or_none():
                    db.add(ChatRoomMember(user_id=user_id, room_id=man_room.id))

    # 3b. Canal de reportes si este usuario ES manager (tiene subordinados)
    reports_res = await db.execute(select(User).where(User.manager_id == user_id))
    reports = reports_res.scalars().all()
    if reports:
        own_room_res = await db.execute(
            select(ChatRoom).where(ChatRoom.room_type == "HIERARCHY", ChatRoom.manager_id == user_id)
        )
        own_room = own_room_res.scalar_one_or_none()
        if not own_room:
            own_room = ChatRoom(
                id=uuid.uuid4().hex,
                name=f"Reportes de {current_user.full_name or current_user.email}",
                room_type="HIERARCHY",
                manager_id=user_id
            )
            db.add(own_room)
            await db.flush()
            # Unirse como manager
            db.add(ChatRoomMember(user_id=user_id, room_id=own_room.id))
            
        # Unir a todos los subordinados activos
        for rep in reports:
            rep_mem = await db.execute(
                select(ChatRoomMember).where(ChatRoomMember.room_id == own_room.id, ChatRoomMember.user_id == rep.id)
            )
            if not rep_mem.scalar_one_or_none():
                db.add(ChatRoomMember(user_id=rep.id, room_id=own_room.id))

    await db.commit()


# --- REST Endpoints ---

@router.get("/rooms", response_model=List[RoomResponse])
async def list_chat_rooms(
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Obtiene la lista de salas del usuario con auto-suscripción en base a departamento/jerarquía.
    """
    uid = _get_user_id(user_payload)
    
    # Obtener el objeto User completo de base de datos
    user_res = await db.execute(select(User).where(User.id == uid))
    current_user = user_res.scalar_one_or_none()
    if not current_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado en el tenant activo")

    # Aprovisionar salas automáticas
    await _auto_provision_rooms(db, current_user)

    # Buscar salas asociadas en las que es miembro
    rooms_query = select(ChatRoom, ChatRoomMember.unread_count)\
        .join(ChatRoomMember, ChatRoomMember.room_id == ChatRoom.id)\
        .where(ChatRoomMember.user_id == uid)
        
    result = await db.execute(rooms_query)
    rooms_data = result.all()

    response = []
    for room, unread in rooms_data:
        # Resolver nombre para DMs
        name = room.name
        if room.room_type == "DIRECT":
            # Buscar el otro miembro del DM
            other_mem_res = await db.execute(
                select(User)\
                    .join(ChatRoomMember, ChatRoomMember.user_id == User.id)\
                    .where(ChatRoomMember.room_id == room.id, ChatRoomMember.user_id != uid)
            )
            other_user = other_mem_res.scalar_one_or_none()
            name = other_user.full_name or other_user.email if other_user else "Usuario SAS"

        # Buscar el último mensaje de esta sala
        last_msg_res = await db.execute(
            select(ChatMessage).where(ChatMessage.room_id == room.id).order_by(ChatMessage.created_at.desc()).limit(1)
        )
        last_msg = last_msg_res.scalar_one_or_none()
        
        last_text = None
        last_time = None
        if last_msg:
            # 90 days expiration filter (return null if expired, clean-up handles actual deletion)
            if last_msg.created_at >= datetime.now(timezone.utc) - timedelta(days=90):
                last_text = last_msg.content
                last_time = last_msg.created_at.isoformat()

        response.append(RoomResponse(
            id=room.id,
            name=name,
            room_type=room.room_type,
            department=room.department,
            team_id=room.team_id,
            manager_id=room.manager_id,
            unread_count=unread,
            last_message=last_text,
            last_message_time=last_time
        ))
        
    return response


@router.get("/rooms/{room_id}/messages", response_model=CursorPaginatedResponse[MessageResponse])
async def get_room_messages(
    room_id: str,
    cursor: Optional[str] = Query(None, description="ISO timestamp del ultimo mensaje recibido (keyset pagination)"),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Obtiene el historial de mensajes de la sala con cursor pagination basada en created_at.
    Aplica la politica de retencion de 90 dias.
    """
    uid = _get_user_id(user_payload)

    mem_res = await db.execute(
        select(ChatRoomMember).where(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == uid)
    )
    if not mem_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="No tienes acceso a esta sala de chat")

    limit_date = datetime.now(timezone.utc) - timedelta(days=90)
    await db.execute(
        delete(ChatMessage).where(ChatMessage.room_id == room_id, ChatMessage.created_at < limit_date)
    )
    from sqlalchemy import update
    await db.execute(
        update(ChatRoomMember)
        .where(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == uid)
        .values(unread_count=0)
    )
    await db.commit()

    query = (
        select(ChatMessage, User.full_name, User.email)
        .join(User, User.id == ChatMessage.sender_id)
        .where(ChatMessage.room_id == room_id)
    )

    parsed_cursor = None
    if cursor:
        try:
            parsed_cursor = datetime.fromisoformat(cursor)
        except (ValueError, TypeError):
            parsed_cursor = None

    result = await paginate_cursor(
        db, query,
        cursor_column=ChatMessage.created_at,
        cursor=parsed_cursor.isoformat() if parsed_cursor else None,
        size=size,
        raw_items=True
    )

    response = []
    for row in result["items"]:
        msg, full_name, email = row[0], row[1], row[2]
        reply_count_res = await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.parent_id == msg.id)
        )
        reply_count = reply_count_res.scalar() or 0
        response.append(MessageResponse(
            id=msg.id,
            room_id=msg.room_id,
            sender_id=msg.sender_id,
            sender_name=full_name or email or "",
            content=msg.content,
            attachment_url=msg.attachment_url,
            attachment_name=msg.attachment_name,
            parent_id=msg.parent_id,
            reactions=msg.reactions or {},
            reply_count=reply_count,
            created_at=msg.created_at.isoformat()
        ))

    return CursorPaginatedResponse(
        items=response,
        next_cursor=result["next_cursor"],
        has_more=result["has_more"]
    )


@router.get("/messages/search", response_model=CursorPaginatedResponse[SearchResultResponse])
async def search_messages(
    q: str,
    room_id: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    uid = _get_user_id(user_payload)
    member_rooms_subq = select(ChatRoomMember.room_id).where(ChatRoomMember.user_id == uid)
    member_rooms_res = await db.execute(member_rooms_subq)
    member_room_ids = [row[0] for row in member_rooms_res.all()]
    if not member_room_ids:
        return CursorPaginatedResponse(items=[], next_cursor=None, has_more=False)

    query = (
        select(ChatMessage, User.full_name, User.email, ChatRoom.name)
        .join(User, User.id == ChatMessage.sender_id)
        .join(ChatRoom, ChatRoom.id == ChatMessage.room_id)
        .where(ChatMessage.room_id.in_(member_room_ids))
    )
    if room_id:
        query = query.where(ChatMessage.room_id == room_id)

    raw_rows = await db.execute(query.order_by(ChatMessage.created_at.desc()))
    all_rows = raw_rows.all()

    search_term = q.lower()
    matched = []
    for row in all_rows:
        msg, full_name, email, room_name = row[0], row[1], row[2], row[3]
        try:
            decrypted = msg.content
        except Exception:
            decrypted = ""
        if search_term in decrypted.lower():
            snippet = decrypted[:200] if len(decrypted) > 200 else decrypted
            matched.append(SearchResultResponse(
                id=msg.id,
                room_id=msg.room_id,
                room_name=room_name,
                sender_id=msg.sender_id,
                sender_name=full_name or email or "",
                content_snippet=snippet,
                created_at=msg.created_at.isoformat()
            ))

    total = len(matched)
    offset = (page - 1) * limit
    page_items = matched[offset:offset + limit]
    next_cursor_val = str(page + 1) if offset + limit < total else None
    has_more = offset + limit < total

    return CursorPaginatedResponse(
        items=page_items,
        next_cursor=next_cursor_val,
        has_more=has_more
    )


@router.get("/rooms/{room_id}/messages/{message_id}/thread", response_model=List[MessageResponse])
async def get_thread_messages(
    room_id: str,
    message_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    uid = _get_user_id(user_payload)
    mem_res = await db.execute(
        select(ChatRoomMember).where(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == uid)
    )
    if not mem_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="No tienes acceso a esta sala de chat")

    parent_res = await db.execute(
        select(ChatMessage).where(ChatMessage.id == message_id, ChatMessage.room_id == room_id)
    )
    parent_msg = parent_res.scalar_one_or_none()
    if not parent_msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")

    thread_query = (
        select(ChatMessage, User.full_name, User.email)
        .join(User, User.id == ChatMessage.sender_id)
        .where(ChatMessage.parent_id == message_id)
        .order_by(ChatMessage.created_at.asc())
    )
    result = await db.execute(thread_query)
    rows = result.all()

    return [
        MessageResponse(
            id=msg.id,
            room_id=msg.room_id,
            sender_id=msg.sender_id,
            sender_name=full_name or email or "",
            content=msg.content,
            attachment_url=msg.attachment_url,
            attachment_name=msg.attachment_name,
            parent_id=msg.parent_id,
            reactions=msg.reactions or {},
            reply_count=0,
            created_at=msg.created_at.isoformat()
        )
        for msg, full_name, email in rows
    ]


@limiter.limit("60/minute")
@router.post("/rooms/{room_id}/messages/{message_id}/reply", response_model=MessageResponse)
async def reply_to_message(
    room_id: str,
    message_id: str,
    payload: ThreadMessageCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    uid = _get_user_id(user_payload)
    mem_res = await db.execute(
        select(ChatRoomMember).where(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == uid)
    )
    if not mem_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="No tienes acceso a esta sala de chat")

    parent_res = await db.execute(
        select(ChatMessage).where(ChatMessage.id == message_id, ChatMessage.room_id == room_id)
    )
    parent_msg = parent_res.scalar_one_or_none()
    if not parent_msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")

    msg = ChatMessage(
        id=uuid.uuid4().hex,
        room_id=room_id,
        sender_id=uid,
        parent_id=message_id
    )
    msg.content = payload.content
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    sender_res = await db.execute(select(User).where(User.id == uid))
    sender = sender_res.scalar_one()

    reply_count_res = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.parent_id == message_id)
    )
    reply_count = reply_count_res.scalar() or 0

    broadcast_payload = {
        "action": "thread_reply",
        "data": {
            "id": msg.id,
            "room_id": room_id,
            "parent_id": message_id,
            "sender_id": uid,
            "sender_name": sender.full_name or sender.email,
            "content": payload.content,
            "created_at": msg.created_at.isoformat(),
            "reply_count": reply_count
        }
    }
    await ws_manager.broadcast_to_room(db, room_id, broadcast_payload)

    return MessageResponse(
        id=msg.id,
        room_id=msg.room_id,
        sender_id=msg.sender_id,
        sender_name=sender.full_name or sender.email or "",
        content=msg.content,
        parent_id=msg.parent_id,
        created_at=msg.created_at.isoformat()
    )


@router.post("/rooms/{room_id}/messages/{message_id}/react", response_model=MessageResponse)
async def react_to_message(
    room_id: str,
    message_id: str,
    payload: ReactionPayload,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    uid = _get_user_id(user_payload)
    mem_res = await db.execute(
        select(ChatRoomMember).where(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == uid)
    )
    if not mem_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="No tienes acceso a esta sala de chat")

    msg_res = await db.execute(
        select(ChatMessage).where(ChatMessage.id == message_id, ChatMessage.room_id == room_id)
    )
    msg = msg_res.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")

    reactions = msg.reactions or {}
    emoji = payload.emoji

    if emoji not in reactions:
        reactions[emoji] = []
    if uid in reactions[emoji]:
        reactions[emoji].remove(uid)
    else:
        reactions[emoji].append(uid)

    if not reactions[emoji]:
        del reactions[emoji]

    msg.reactions = reactions
    await db.commit()
    await db.refresh(msg)

    sender_res = await db.execute(select(User).where(User.id == msg.sender_id))
    sender = sender_res.scalar_one()

    reply_count_res = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.parent_id == message_id)
    )
    reply_count = reply_count_res.scalar() or 0

    broadcast_payload = {
        "action": "reaction",
        "data": {
            "message_id": message_id,
            "room_id": room_id,
            "reactions": reactions
        }
    }
    await ws_manager.broadcast_to_room(db, room_id, broadcast_payload)

    return MessageResponse(
        id=msg.id,
        room_id=msg.room_id,
        sender_id=msg.sender_id,
        sender_name=sender.full_name or sender.email or "",
        content=msg.content,
        attachment_url=msg.attachment_url,
        attachment_name=msg.attachment_name,
        parent_id=msg.parent_id,
        reactions=reactions,
        reply_count=reply_count,
        created_at=msg.created_at.isoformat()
    )


@router.post("/rooms/direct", response_model=RoomResponse)
async def create_direct_room(
    payload: DirectRoomCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Crea o recupera una sala DM. Restringe la creación a usuarios de la misma jerarquía o departamento.
    """
    uid = _get_user_id(user_payload)
    target_uid = payload.target_user_id
    
    if uid == target_uid:
        raise HTTPException(status_code=400, detail="No puedes abrir un chat directo contigo mismo")

    # Obtener ambos perfiles
    user_res = await db.execute(select(User).where(User.id == uid))
    current_user = user_res.scalar_one_or_none()
    
    target_res = await db.execute(select(User).where(User.id == target_uid))
    target_user = target_res.scalar_one_or_none()

    if not current_user or not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Validación de límites de comunicación: mismo departamento o reporte jerárquico directo
    is_same_dept = current_user.department and current_user.department == target_user.department
    is_reporting = current_user.manager_id == target_user.id or target_user.manager_id == current_user.id
    
    if not (is_same_dept or is_reporting):
        raise HTTPException(
            status_code=403,
            detail="Los chats directos están limitados a empleados del mismo departamento o de la misma línea jerárquica de reporte."
        )

    # Buscar si ya existe una sala DIRECT que tenga a ambos usuarios de miembros
    existing_dm_query = select(ChatRoom.id)\
        .join(ChatRoomMember, ChatRoomMember.room_id == ChatRoom.id)\
        .where(ChatRoom.room_type == "DIRECT", ChatRoomMember.user_id == uid)\
        .intersect(
            select(ChatRoom.id)\
                .join(ChatRoomMember, ChatRoomMember.room_id == ChatRoom.id)\
                .where(ChatRoom.room_type == "DIRECT", ChatRoomMember.user_id == target_uid)
        )
        
    existing_dm_res = await db.execute(existing_dm_query)
    existing_room_id = existing_dm_res.scalar()

    if existing_room_id:
        room_res = await db.execute(select(ChatRoom).where(ChatRoom.id == existing_room_id))
        room = room_res.scalar_one()
        return RoomResponse(
            id=room.id,
            name=target_user.full_name or target_user.email,
            room_type=room.room_type
        )

    # Crear nueva sala
    new_room = ChatRoom(
        id=uuid.uuid4().hex,
        room_type="DIRECT"
    )
    db.add(new_room)
    await db.flush()

    db.add(ChatRoomMember(user_id=uid, room_id=new_room.id))
    db.add(ChatRoomMember(user_id=target_uid, room_id=new_room.id))
    await db.commit()

    return RoomResponse(
        id=new_room.id,
        name=target_user.full_name or target_user.email,
        room_type=new_room.room_type
    )


@router.post("/rooms/{room_id}/upload")
async def upload_chat_file(
    room_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Sube archivos, documentos e imágenes compartidos en la sala y los almacena localmente.
    """
    uid = _get_user_id(user_payload)
    
    # Validar membresía
    mem_res = await db.execute(
        select(ChatRoomMember).where(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == uid)
    )
    if not mem_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="No tienes acceso a esta sala")

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    
    # Nombre de archivo único seguro
    ext = file.filename.split(".")[-1] if "." in file.filename else "dat"
    filename = f"chat_{uuid.uuid4().hex[:12]}.{ext}"
    file_path = os.path.join(UPLOADS_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "success": True,
        "url": f"/uploads/{filename}",
        "name": file.filename
    }


# --- WebSockets Connection Manager ---

class ChatConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self._redis_listener: Optional[asyncio.Task] = None
        self._pubsub = None

    async def _ensure_redis_listener(self):
        if self._redis_listener and not self._redis_listener.done():
            return
        self._redis_listener = asyncio.create_task(self._listen_redis())

    async def _listen_redis(self):
        try:
            from app.core.redis import get_redis
            r = await get_redis()
            self._pubsub = r.pubsub()
            await self._pubsub.subscribe("chat:ws:broadcast")
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        user_ids = data.get("user_ids", [])
                        payload = data.get("payload", {})
                        for uid in user_ids:
                            if uid in self.active_connections:
                                for conn in self.active_connections[uid]:
                                    try:
                                        await conn.send_json(payload)
                                    except Exception:
                                        pass
                    except Exception:
                        pass
        except Exception:
            pass

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        await self._ensure_redis_listener()

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def broadcast_to_room(self, db: AsyncSession, room_id: str, message: dict):
        members_res = await db.execute(
            select(ChatRoomMember.user_id).where(ChatRoomMember.room_id == room_id)
        )
        member_ids = list(members_res.scalars().all())

        for user_id in member_ids:
            if user_id in self.active_connections:
                for connection in self.active_connections[user_id]:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        pass

        try:
            from app.core.redis import get_redis
            r = await get_redis()
            await r.publish("chat:ws:broadcast", json.dumps({
                "user_ids": member_ids,
                "payload": message,
            }))
        except Exception:
            pass

ws_manager = ChatConnectionManager()


@router.websocket("/ws")
async def chat_websocket_endpoint(websocket: WebSocket):
    """
    Canal de comunicación en tiempo real para mensajería instantánea.
    Autentica con token JWT enviado en query string o cookie de sesión.
    """
    token = websocket.query_params.get("token")
    if not token:
        token = websocket.cookies.get("access_token")
        
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = auth_verifier.verify(token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = _get_user_id(payload)
    app_metadata = payload.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or payload.get("tenant_id")
    
    if not tenant_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    tenant_schema = f"tenant_{tenant_id}"
    sessionmaker = _get_or_create_sessionmaker(tenant_schema)

    # Registrar conexión
    await ws_manager.connect(user_id, websocket)

    try:
        while True:
            # Recibir datos del cliente
            data = await websocket.receive_json()
            
            action = data.get("action")
            room_id = data.get("room_id")
            
            if not room_id or not action:
                continue

            async with sessionmaker() as db:
                # Verificar membresía
                mem_res = await db.execute(
                    select(ChatRoomMember).where(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == user_id)
                )
                if not mem_res.scalar_one_or_none():
                    continue

                if action == "message":
                    content = data.get("content", "").strip()
                    attachment_url = data.get("attachment_url")
                    attachment_name = data.get("attachment_name")
                    parent_id = data.get("parent_id")

                    if not content and not attachment_url:
                        continue

                    msg = ChatMessage(
                        id=uuid.uuid4().hex,
                        room_id=room_id,
                        sender_id=user_id,
                        attachment_url=attachment_url,
                        attachment_name=attachment_name,
                        parent_id=parent_id
                    )
                    msg.content = content
                    db.add(msg)
                    
                    # Incrementar unread count del resto de miembros
                    from sqlalchemy import update
                    await db.execute(
                        update(ChatRoomMember)\
                            .where(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id != user_id)\
                            .values(unread_count=ChatRoomMember.unread_count + 1)
                    )
                    
                    await db.commit()

                    # Resolver nombre del remitente
                    sender_res = await db.execute(select(User).where(User.id == user_id))
                    sender = sender_res.scalar_one()

                    # Propagar mensaje en tiempo real
                    payload = {
                        "action": "message",
                        "data": {
                            "id": msg.id,
                            "room_id": room_id,
                            "sender_id": user_id,
                            "sender_name": sender.full_name or sender.email,
                            "content": content,
                            "attachment_url": attachment_url,
                            "attachment_name": attachment_name,
                            "parent_id": parent_id,
                            "reactions": {},
                            "reply_count": 0,
                            "created_at": msg.created_at.isoformat()
                        }
                    }
                    await ws_manager.broadcast_to_room(db, room_id, payload)

                elif action == "typing":
                    # Propagar estado de escribiendo
                    sender_res = await db.execute(select(User).where(User.id == user_id))
                    sender = sender_res.scalar_one()
                    
                    payload = {
                        "action": "typing",
                        "room_id": room_id,
                        "user_id": user_id,
                        "user_name": sender.full_name or sender.email,
                        "is_typing": data.get("is_typing", False)
                    }
                    await ws_manager.broadcast_to_room(db, room_id, payload)

    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, websocket)
    except Exception as e:
        logger.error(f"Error en WebSocket de chat: {e}")
        ws_manager.disconnect(user_id, websocket)


# --- Collaborative Sessions Router ---

collab_router = APIRouter()


class CreateCollabRoomBody(BaseModel):
    agent_session_id: str
    user_ids: list[str]
    agent_id: str


class SendCollabMessageBody(BaseModel):
    content: str


@collab_router.post("/rooms")
async def create_collab_room(
    body: CreateCollabRoomBody,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.collaborative_session import CollaborativeSession
    room_id = await CollaborativeSession.create_room(
        body.agent_session_id,
        body.user_ids,
        body.agent_id,
        db,
    )
    return {"room_id": room_id, "status": "created"}


@collab_router.post("/rooms/{room_id}/join")
async def join_collab_room(
    room_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.collaborative_session import CollaborativeSession
    uid = _get_user_id(current_user)
    try:
        result = await CollaborativeSession.add_participant(room_id, uid, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@limiter.limit("60/minute")
@collab_router.post("/rooms/{room_id}/message")
async def send_collab_message(
    room_id: str,
    body: SendCollabMessageBody,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.collaborative_session import CollaborativeSession
    from app.services.agent_runtime import execute_agent_run
    uid = _get_user_id(current_user)
    try:
        result = await CollaborativeSession.send_user_message(room_id, uid, body.content, db)
        agent_id = result.get("agent_id")
        if agent_id:
            try:
                agent_response = await execute_agent_run(
                    db, agent_id,
                    {"message": body.content, "user_id": uid},
                    trigger_source="collaborative"
                )
                reply = agent_response.get("reply") or agent_response.get("output_result", {}).get("reply", "")
                if reply:
                    await CollaborativeSession.broadcast_agent_response(room_id, reply, agent_id, db)
                return {**result, "agent_reply": reply}
            except Exception as agent_err:
                logger.error(f"Agent execution failed in collaborative room: {agent_err}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@collab_router.get("/rooms/{room_id}/participants")
async def list_collab_participants(
    room_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.collaborative_session import CollaborativeSession
    participants = await CollaborativeSession.get_room_participants(room_id, db)
    return {"room_id": room_id, "participants": participants}


@collab_router.websocket("/rooms/{room_id}/ws")
async def collab_websocket_endpoint(websocket: WebSocket, room_id: str):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        payload = auth_verifier.verify(token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    uid = _get_user_id(payload)

    from app.services.collaborative_session import CollaborativeSession
    await CollaborativeSession.connect_room_ws(room_id, uid, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "").strip()
            if not content:
                continue
            tenant_schema = f"tenant_{uid}"
            sessionmaker = _get_or_create_sessionmaker(tenant_schema)
            async with sessionmaker() as db:
                try:
                    result = await CollaborativeSession.send_user_message(room_id, uid, content, db)
                    agent_id = result.get("agent_id")
                    if agent_id:
                        try:
                            agent_response = await execute_agent_run(
                                db, agent_id,
                                {"message": content, "user_id": uid},
                                trigger_source="collaborative"
                            )
                            reply = agent_response.get("reply") or agent_response.get("output_result", {}).get("reply", "")
                            if reply:
                                await CollaborativeSession.broadcast_agent_response(room_id, reply, agent_id, db)
                        except Exception as agent_err:
                            logger.error(f"Collaborative agent error: {agent_err}")
                except Exception as e:
                    logger.error(f"Collaborative message error: {e}")
    except WebSocketDisconnect:
        CollaborativeSession.disconnect_room_ws(room_id, uid, websocket)
    except Exception as e:
        logger.error(f"Collaborative WS error: {e}")
        CollaborativeSession.disconnect_room_ws(room_id, uid, websocket)
