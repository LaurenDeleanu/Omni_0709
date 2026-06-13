import logging
import difflib
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.agent import PromptVersion

logger = logging.getLogger(__name__)


class PromptVersionControl:
    """
    Manages versioned snapshots of agent system prompts with rollback, diff, and history capabilities.
    Uses the PromptVersion DB model for persistence.
    """

    async def save_version(
        self,
        agent_id: str,
        system_prompt: str,
        components: list,
        changed_by: str,
        db: AsyncSession,
        change_description: str = "",
    ) -> str:
        max_ver_res = await db.execute(
            select(func.max(PromptVersion.version_number)).where(
                PromptVersion.agent_id == agent_id
            )
        )
        next_version = (max_ver_res.scalar() or 0) + 1

        version = PromptVersion(
            id=uuid.uuid4().hex,
            agent_id=agent_id,
            version_number=next_version,
            system_prompt=system_prompt,
            prompt_components=components if components else None,
            changed_by=changed_by,
            change_description=change_description,
        )
        db.add(version)
        await db.flush()
        logger.info(
            f"Prompt version {next_version} saved for agent {agent_id} by {changed_by}"
        )
        return version.id

    async def get_version(
        self, agent_id: str, version_number: int, db: AsyncSession
    ) -> Optional[dict]:
        res = await db.execute(
            select(PromptVersion).where(
                PromptVersion.agent_id == agent_id,
                PromptVersion.version_number == version_number,
            )
        )
        row = res.scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id,
            "agent_id": row.agent_id,
            "version_number": row.version_number,
            "system_prompt": row.system_prompt,
            "prompt_components": row.prompt_components,
            "changed_by": row.changed_by,
            "change_description": row.change_description,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def get_latest_version(
        self, agent_id: str, db: AsyncSession
    ) -> Optional[dict]:
        res = await db.execute(
            select(PromptVersion)
            .where(PromptVersion.agent_id == agent_id)
            .order_by(desc(PromptVersion.version_number))
            .limit(1)
        )
        row = res.scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id,
            "agent_id": row.agent_id,
            "version_number": row.version_number,
            "system_prompt": row.system_prompt,
            "prompt_components": row.prompt_components,
            "changed_by": row.changed_by,
            "change_description": row.change_description,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def rollback_to_version(
        self,
        agent_id: str,
        version_number: int,
        db: AsyncSession,
        changed_by: str = "system",
    ) -> Optional[dict]:
        target = await self.get_version(agent_id, version_number, db)
        if not target:
            return None

        new_version_id = await self.save_version(
            agent_id=agent_id,
            system_prompt=target["system_prompt"],
            components=target["prompt_components"] or [],
            changed_by=changed_by,
            db=db,
            change_description=f"Rollback to version {version_number}",
        )
        new_version = await self.get_version(
            agent_id,
            (await db.execute(
                select(PromptVersion.version_number).where(PromptVersion.id == new_version_id)
            )).scalar_one(),
            db,
        )
        return new_version

    async def diff_versions(
        self,
        agent_id: str,
        version_a: int,
        version_b: int,
        db: AsyncSession,
    ) -> dict:
        v_a = await self.get_version(agent_id, version_a, db)
        v_b = await self.get_version(agent_id, version_b, db)
        if not v_a or not v_b:
            return {"error": "One or both versions not found"}

        text_a = (v_a["system_prompt"] or "").splitlines(keepends=True)
        text_b = (v_b["system_prompt"] or "").splitlines(keepends=True)

        differ = difflib.unified_diff(text_a, text_b, fromfile=f"v{version_a}", tofile=f"v{version_b}")
        diff_output = list(differ)

        added_lines = [l[1:] for l in diff_output if l.startswith("+") and not l.startswith("+++")]
        removed_lines = [l[1:] for l in diff_output if l.startswith("-") and not l.startswith("---")]
        unchanged = [l[1:] for l in diff_output if l.startswith(" ") or l.startswith("@@")]

        matcher = difflib.SequenceMatcher(None, v_a["system_prompt"] or "", v_b["system_prompt"] or "")
        similarity = round(matcher.ratio(), 4)

        return {
            "version_a": version_a,
            "version_b": version_b,
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "unchanged_preview": unchanged[:10],
            "similarity_score": similarity,
            "full_diff": "".join(diff_output) if diff_output else "No differences.",
        }

    async def list_versions(
        self,
        agent_id: str,
        db: AsyncSession,
        limit: int = 20,
    ) -> list:
        res = await db.execute(
            select(PromptVersion)
            .where(PromptVersion.agent_id == agent_id)
            .order_by(desc(PromptVersion.version_number))
            .limit(limit)
        )
        rows = res.scalars().all()
        return [
            {
                "id": r.id,
                "agent_id": r.agent_id,
                "version_number": r.version_number,
                "changed_by": r.changed_by,
                "change_description": r.change_description,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "prompt_preview": (r.system_prompt or "")[:120] + "...",
            }
            for r in rows
        ]


_prompt_version_control = PromptVersionControl()


def get_prompt_version_control() -> PromptVersionControl:
    return _prompt_version_control
