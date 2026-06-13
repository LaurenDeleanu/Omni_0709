import os
import uuid
import logging
import subprocess
import difflib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.models.branch_edit import BranchSession, FileProposal

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PATCHES_DIR = os.path.join(WORKSPACE_ROOT, ".omni_patches")


class BranchEditManager:
    def __init__(self):
        self._active_sessions: Dict[str, BranchSession] = {}

    async def initialize_branch(
        self, agent_id: str, base_branch: str, user_id: str, db: AsyncSession
    ) -> BranchSession:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        branch_name = f"agent/{agent_id[:8]}/{timestamp}"

        try:
            from app.services.local_git_service import create_branch as git_create_branch
            await git_create_branch(branch_name, base_branch)
        except Exception as e:
            logger.warning(f"Could not create git branch {branch_name}: {e}")

        session = BranchSession(
            agent_id=agent_id,
            user_id=user_id,
            branch_name=branch_name,
            base_branch=base_branch,
            status="active",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        self._active_sessions[agent_id] = session
        return session

    async def write_file_proposal(
        self,
        branch_session_id: str,
        file_path: str,
        content: str,
        original_content: str,
        reason: str,
        db: AsyncSession,
        agent_id: str = "",
    ) -> FileProposal:
        diff_text = self._compute_diff(original_content, content)

        proposal = FileProposal(
            branch_session_id=branch_session_id,
            agent_id=agent_id,
            file_path=file_path,
            original_content=original_content,
            proposed_content=content,
            diff_text=diff_text,
            reason=reason,
            status="pending",
            proposed_by=agent_id,
        )
        db.add(proposal)

        session_res = await db.execute(
            select(BranchSession).where(BranchSession.id == branch_session_id)
        )
        session = session_res.scalar_one_or_none()
        if session:
            session.total_proposals = (session.total_proposals or 0) + 1

        await db.commit()
        await db.refresh(proposal)
        return proposal

    async def apply_proposal(self, proposal_id: str, approved_by: str, db: AsyncSession) -> FileProposal:
        proposal_res = await db.execute(
            select(FileProposal).where(FileProposal.id == proposal_id)
        )
        proposal = proposal_res.scalar_one_or_none()
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        if proposal.status != "pending":
            raise ValueError(f"Proposal {proposal_id} is already {proposal.status}")

        self._write_to_disk(proposal.file_path, proposal.proposed_content)

        proposal.status = "applied"
        proposal.reviewed_by = approved_by
        proposal.reviewed_at = datetime.now(timezone.utc)

        session_res = await db.execute(
            select(BranchSession).where(BranchSession.id == proposal.branch_session_id)
        )
        session = session_res.scalar_one_or_none()
        if session:
            session.applied_proposals = (session.applied_proposals or 0) + 1

        await db.commit()
        await db.refresh(proposal)

        await self._check_session_complete(proposal.branch_session_id, db)
        return proposal

    async def reject_proposal(
        self, proposal_id: str, rejected_by: str, reason: str, db: AsyncSession
    ) -> FileProposal:
        proposal_res = await db.execute(
            select(FileProposal).where(FileProposal.id == proposal_id)
        )
        proposal = proposal_res.scalar_one_or_none()
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        proposal.status = "rejected"
        proposal.reviewed_by = rejected_by
        proposal.review_notes = reason
        proposal.reviewed_at = datetime.now(timezone.utc)

        session_res = await db.execute(
            select(BranchSession).where(BranchSession.id == proposal.branch_session_id)
        )
        session = session_res.scalar_one_or_none()
        if session:
            session.rejected_proposals = (session.rejected_proposals or 0) + 1

        await db.commit()
        await db.refresh(proposal)
        await self._check_session_complete(proposal.branch_session_id, db)
        return proposal

    async def get_session_proposals(
        self, branch_session_id: str, db: AsyncSession, status_filter: Optional[str] = None
    ) -> List[FileProposal]:
        query = select(FileProposal).where(FileProposal.branch_session_id == branch_session_id)
        if status_filter:
            query = query.where(FileProposal.status == status_filter)
        query = query.order_by(FileProposal.created_at)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_diff(self, proposal_id: str, db: AsyncSession) -> str:
        proposal_res = await db.execute(
            select(FileProposal).where(FileProposal.id == proposal_id)
        )
        proposal = proposal_res.scalar_one_or_none()
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        return proposal.diff_text or ""

    async def create_patch_file(self, branch_session_id: str, db: AsyncSession) -> str:
        proposals = await self.get_session_proposals(branch_session_id, db, status_filter="pending")
        if not proposals:
            raise ValueError("No pending proposals to create patch from")

        os.makedirs(PATCHES_DIR, exist_ok=True)
        patch_path = os.path.join(PATCHES_DIR, f"{branch_session_id}.patch")

        with open(patch_path, "w", encoding="utf-8") as f:
            for proposal in proposals:
                if proposal.diff_text:
                    f.write(proposal.diff_text)
                    f.write("\n")

        return patch_path

    async def apply_patch_file(self, patch_path: str, db: AsyncSession) -> str:
        try:
            from app.services.local_git_service import apply_patch as git_apply
            result = await git_apply(patch_path)
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to apply patch {patch_path}: {e}")

    async def apply_all_pending(self, branch_session_id: str, approved_by: str, db: AsyncSession) -> Dict[str, Any]:
        proposals = await self.get_session_proposals(branch_session_id, db, status_filter="pending")
        applied_count = 0
        errors = []

        for proposal in proposals:
            try:
                await self.apply_proposal(proposal.id, approved_by, db)
                applied_count += 1
            except Exception as e:
                errors.append({"proposal_id": proposal.id, "error": str(e)})

        session_res = await db.execute(
            select(BranchSession).where(BranchSession.id == branch_session_id)
        )
        session = session_res.scalar_one_or_none()

        return {
            "applied": applied_count,
            "total": len(proposals),
            "errors": errors,
            "branch_status": session.status if session else "unknown",
        }

    async def create_pr_from_session(
        self, branch_session_id: str, title: str, body: str, db: AsyncSession
    ) -> Dict[str, Any]:
        session_res = await db.execute(
            select(BranchSession).where(BranchSession.id == branch_session_id)
        )
        session = session_res.scalar_one_or_none()
        if not session:
            raise ValueError(f"Session {branch_session_id} not found")

        proposals = await self.get_session_proposals(branch_session_id, db, status_filter="pending")
        if not proposals:
            raise ValueError("No pending proposals to commit")

        from app.services.local_git_service import (
            checkout_branch,
            commit_changes,
            get_current_branch,
        )

        original_branch = await get_current_branch()

        try:
            await checkout_branch(session.branch_name)

            for proposal in proposals:
                self._write_to_disk(proposal.file_path, proposal.proposed_content)

            files = [p.file_path for p in proposals]
            commit_hash = await commit_changes(
                f"{title}\n\n{body}\n\nBranch session: {branch_session_id}",
                files,
            )

            for proposal in proposals:
                proposal.status = "applied"
                proposal.reviewed_at = datetime.now(timezone.utc)

            session.status = "completed"
            session.completed_at = datetime.now(timezone.utc)
            session.applied_proposals = len(proposals)
            await db.commit()

            await checkout_branch(original_branch)

            return {
                "commit_hash": commit_hash,
                "branch": session.branch_name,
                "files_committed": len(proposals),
            }

        except Exception as e:
            try:
                await checkout_branch(original_branch)
            except Exception:
                pass
            raise RuntimeError(f"Failed to create PR/commit from session: {e}")

    async def get_edit_mode(self, agent_id: str, db: AsyncSession) -> Dict[str, Any]:
        from app.models.agent import Agent
        agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = agent_res.scalar_one_or_none()

        if not agent:
            return {"mode": "direct", "auto_create_branch": False, "require_approval": True, "repo_url": ""}

        settings = agent.agent_settings or {}
        edit_mode = settings.get("edit_mode", "direct")

        return {
            "mode": edit_mode,
            "auto_create_branch": settings.get("auto_create_branch", edit_mode == "proposal"),
            "require_approval": settings.get("require_approval", True),
            "repo_url": settings.get("repo_url", ""),
        }

    async def set_edit_mode(self, agent_id: str, settings: Dict[str, Any], db: AsyncSession) -> bool:
        from app.models.agent import Agent
        agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = agent_res.scalar_one_or_none()
        if not agent:
            return False

        current_settings = dict(agent.agent_settings) if agent.agent_settings else {}
        current_settings["edit_mode"] = settings.get("mode", "direct")
        current_settings["auto_create_branch"] = settings.get("auto_create_branch", False)
        current_settings["require_approval"] = settings.get("require_approval", True)
        if "repo_url" in settings:
            current_settings["repo_url"] = settings["repo_url"]

        agent.agent_settings = current_settings
        await db.commit()
        return True

    async def _check_session_complete(self, branch_session_id: str, db: AsyncSession):
        session_res = await db.execute(
            select(BranchSession).where(BranchSession.id == branch_session_id)
        )
        session = session_res.scalar_one_or_none()
        if not session:
            return

        all_proposals_res = await db.execute(
            select(FileProposal).where(FileProposal.branch_session_id == branch_session_id)
        )
        all_proposals = list(all_proposals_res.scalars().all())

        pending = [p for p in all_proposals if p.status == "pending"]
        if not pending and all_proposals:
            session.status = "completed"
            session.completed_at = datetime.now(timezone.utc)
            session.applied_proposals = sum(1 for p in all_proposals if p.status == "applied")
            session.rejected_proposals = sum(1 for p in all_proposals if p.status == "rejected")
            await db.commit()

    def _compute_diff(self, original: str, new: str) -> str:
        original_lines = original.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)

        if not original_lines or not original_lines[-1].endswith("\n"):
            if original_lines:
                original_lines[-1] = original_lines[-1] + "\n"
        if not new_lines or not new_lines[-1].endswith("\n"):
            if new_lines:
                new_lines[-1] = new_lines[-1] + "\n"

        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile="a/original",
            tofile="b/proposed",
            lineterm="",
        )
        return "\n".join(diff)

    def _write_to_disk(self, file_path: str, content: str):
        full_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, file_path.lstrip("/\\")))
        dir_path = os.path.dirname(full_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def get_active_session(self, agent_id: str) -> Optional[BranchSession]:
        return self._active_sessions.get(agent_id)

    def clear_active_session(self, agent_id: str):
        self._active_sessions.pop(agent_id, None)
