import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text

from app.models.agent import Agent, AgentSession, AgentExecutionRun
from app.models.agent import CollaborativeRoom, CollaborativeRoomParticipant, CollaborativeMessage



class CollaborativeSession:
    _room_clients: dict[str, list] = {}

    @classmethod
    async def connect_room_ws(cls, room_id: str, user_id: str, ws):
        await ws.accept()
        if room_id not in cls._room_clients:
            cls._room_clients[room_id] = []
        cls._room_clients[room_id].append({"user_id": user_id, "ws": ws})

    @classmethod
    def disconnect_room_ws(cls, room_id: str, user_id: str, ws):
        if room_id not in cls._room_clients:
            return
        cls._room_clients[room_id] = [
            c for c in cls._room_clients[room_id]
            if not (c["user_id"] == user_id and c["ws"] == ws)
        ]
        if not cls._room_clients[room_id]:
            del cls._room_clients[room_id]

    @classmethod
    async def broadcast_to_room(cls, room_id: str, payload: dict) -> int:
        if room_id not in cls._room_clients:
            return 0
        sent = 0
        dead = []
        for client in cls._room_clients[room_id]:
            try:
                await client["ws"].send_json(payload)
                sent += 1
            except Exception:
                dead.append(client)
        for d in dead:
            cls._room_clients[room_id].remove(d)
        return sent

    @staticmethod
    async def create_room(
        session_id: str,
        user_ids: list[str],
        agent_id: str,
        db: AsyncSession,
    ) -> str:
        room = CollaborativeRoom(
            id=uuid.uuid4().hex,
            agent_session_id=session_id,
            agent_id=agent_id,
            name=None,
            created_by=user_ids[0] if user_ids else "unknown",
            is_active=True,
        )
        db.add(room)
        await db.flush()

        for uid in user_ids:
            participant = CollaborativeRoomParticipant(
                id=uuid.uuid4().hex,
                room_id=room.id,
                user_id=uid,
            )
            db.add(participant)

        await db.commit()

        system_msg = CollaborativeMessage(
            id=uuid.uuid4().hex,
            room_id=room.id,
            sender_user_id=None,
            sender_agent_id=None,
            content=f"Collaborative session started with {len(user_ids)} participant(s).",
            message_type="system",
        )
        db.add(system_msg)
        await db.commit()

        logger.info(f"Collaborative room created: {room.id} for agent {agent_id}")
        return room.id

    @staticmethod
    async def add_participant(
        room_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> dict:
        room_res = await db.execute(
            select(CollaborativeRoom).where(
                CollaborativeRoom.id == room_id,
                CollaborativeRoom.is_active == True,
            )
        )
        room = room_res.scalar_one_or_none()
        if not room:
            raise ValueError(f"Room {room_id} not found or inactive")

        existing = await db.execute(
            select(CollaborativeRoomParticipant).where(
                CollaborativeRoomParticipant.room_id == room_id,
                CollaborativeRoomParticipant.user_id == user_id,
                CollaborativeRoomParticipant.left_at == None,
            )
        )
        if existing.scalar_one_or_none():
            return {"status": "already_joined", "room_id": room_id}

        previously_left = await db.execute(
            select(CollaborativeRoomParticipant).where(
                CollaborativeRoomParticipant.room_id == room_id,
                CollaborativeRoomParticipant.user_id == user_id,
                CollaborativeRoomParticipant.left_at != None,
            )
        )
        prev = previously_left.scalar_one_or_none()
        if prev:
            prev.left_at = None
            prev.joined_at = datetime.now(timezone.utc)
        else:
            participant = CollaborativeRoomParticipant(
                id=uuid.uuid4().hex,
                room_id=room_id,
                user_id=user_id,
            )
            db.add(participant)

        await db.commit()

        history = await CollaborativeSession._get_history(room_id, db)
        return {"status": "joined", "room_id": room_id, "history": history}

    @staticmethod
    async def broadcast_agent_response(
        room_id: str,
        message: str,
        sender_agent_id: str,
        db: AsyncSession,
    ) -> dict:
        msg = CollaborativeMessage(
            id=uuid.uuid4().hex,
            room_id=room_id,
            sender_user_id=None,
            sender_agent_id=sender_agent_id,
            content=message,
            message_type="agent_response",
        )
        db.add(msg)
        await db.commit()

        payload = {
            "type": "agent_response",
            "data": {
                "id": msg.id,
                "room_id": room_id,
                "sender_agent_id": sender_agent_id,
                "content": message,
                "message_type": "agent_response",
                "created_at": msg.created_at.isoformat(),
            },
        }
        sent_count = await CollaborativeSession.broadcast_to_room(room_id, payload)
        return {"message_id": msg.id, "recipients": sent_count}

    @staticmethod
    async def get_room_participants(room_id: str, db: AsyncSession) -> list:
        result = await db.execute(
            select(CollaborativeRoomParticipant).where(
                CollaborativeRoomParticipant.room_id == room_id,
                CollaborativeRoomParticipant.left_at == None,
            )
        )
        participants = result.scalars().all()
        return [{"user_id": p.user_id, "joined_at": p.joined_at.isoformat()} for p in participants]

    @staticmethod
    async def get_room_info(room_id: str, db: AsyncSession) -> Optional[dict]:
        result = await db.execute(
            select(CollaborativeRoom).where(CollaborativeRoom.id == room_id)
        )
        room = result.scalar_one_or_none()
        if not room:
            return None
        participants = await CollaborativeSession.get_room_participants(room_id, db)
        return {
            "id": room.id,
            "agent_id": room.agent_id,
            "agent_session_id": room.agent_session_id,
            "name": room.name,
            "created_by": room.created_by,
            "is_active": room.is_active,
            "created_at": room.created_at.isoformat(),
            "participants": participants,
        }

    @staticmethod
    async def _get_history(room_id: str, db: AsyncSession, limit: int = 50) -> list:
        result = await db.execute(
            select(CollaborativeMessage)
            .where(CollaborativeMessage.room_id == room_id)
            .order_by(CollaborativeMessage.created_at.asc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return [
            {
                "id": m.id,
                "sender_user_id": m.sender_user_id,
                "sender_agent_id": m.sender_agent_id,
                "content": m.content,
                "message_type": m.message_type,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]

    @staticmethod
    async def send_user_message(
        room_id: str,
        user_id: str,
        content: str,
        db: AsyncSession,
    ) -> dict:
        room_res = await db.execute(
            select(CollaborativeRoom).where(
                CollaborativeRoom.id == room_id,
                CollaborativeRoom.is_active == True,
            )
        )
        room = room_res.scalar_one_or_none()
        if not room:
            raise ValueError(f"Room {room_id} not found or inactive")

        msg = CollaborativeMessage(
            id=uuid.uuid4().hex,
            room_id=room_id,
            sender_user_id=user_id,
            sender_agent_id=None,
            content=content,
            message_type="user_message",
        )
        db.add(msg)
        await db.commit()

        payload = {
            "type": "user_message",
            "data": {
                "id": msg.id,
                "room_id": room_id,
                "sender_user_id": user_id,
                "content": content,
                "message_type": "user_message",
                "created_at": msg.created_at.isoformat(),
            },
        }
        sent_count = await CollaborativeSession.broadcast_to_room(room_id, payload)
        return {
            "message_id": msg.id,
            "recipients": sent_count,
            "agent_id": room.agent_id,
            "agent_session_id": room.agent_session_id,
        }
