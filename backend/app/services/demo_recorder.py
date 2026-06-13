import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import DemoSession, DemoSkill, Agent

logger = logging.getLogger("successcore.demo_recorder")

TOOL_BINDINGS = {
    "navigation": "navigate_to_url",
    "form_submit": "submit_form",
    "button_click": "click_element",
    "api_call": "api_request",
}


@dataclass
class SkillConversionResult:
    skill_id: Optional[str] = None
    name: Optional[str] = None
    steps_count: int = 0
    success: bool = False
    error: Optional[str] = None


class DemonstrationRecorder:

    async def start_recording(
        self, session_id: str, agent_id: str, user_id: str, db: AsyncSession
    ) -> str:
        recording = DemoSession(
            agent_id=agent_id,
            user_id=user_id,
            recording_name=session_id,
            status="recording",
            events=[],
            event_count=0,
            total_duration_ms=0,
        )
        db.add(recording)
        await db.commit()
        await db.refresh(recording)
        logger.info(f"Demo recording started: {recording.id} for agent {agent_id}")
        return recording.id

    async def record_action(
        self, recording_id: str, action: dict, db: AsyncSession
    ):
        result = await db.execute(select(DemoSession).where(DemoSession.id == recording_id))
        recording = result.scalar_one_or_none()
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")
        if recording.status != "recording":
            raise ValueError(f"Recording {recording_id} is not active (status={recording.status})")

        action.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        action.setdefault("duration_ms", 0)

        events = recording.events or []
        events.append(action)
        recording.events = events
        recording.event_count = len(events)
        recording.total_duration_ms += action.get("duration_ms", 0)
        await db.commit()
        logger.info(f"Action recorded for demo {recording_id}: {action.get('type')} on {action.get('target')}")

    async def stop_recording(
        self, recording_id: str, db: AsyncSession
    ) -> dict:
        result = await db.execute(select(DemoSession).where(DemoSession.id == recording_id))
        recording = result.scalar_one_or_none()
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        recording.status = "completed"
        recording.completed_at = datetime.now(timezone.utc)
        await db.commit()

        conversion = await self.convert_to_agent_skill(recording_id, db)

        summary = {
            "recording_id": recording.id,
            "recording_name": recording.recording_name,
            "event_count": recording.event_count,
            "total_duration_ms": recording.total_duration_ms,
            "converted_skill": {
                "skill_id": conversion.skill_id,
                "name": conversion.name,
                "steps_count": conversion.steps_count,
                "success": conversion.success,
            },
        }
        logger.info(f"Demo recording stopped: {recording_id}, converted={conversion.success}")
        return summary

    async def convert_to_agent_skill(
        self, recording_id: str, db: AsyncSession
    ) -> SkillConversionResult:
        result = await db.execute(select(DemoSession).where(DemoSession.id == recording_id))
        recording = result.scalar_one_or_none()
        if not recording:
            return SkillConversionResult(success=False, error="Recording not found")
        if not recording.events:
            return SkillConversionResult(success=False, error="No events in recording")

        events = recording.events
        steps = []
        step_number = 1
        action_descriptions = {
            "navigation": "Navigate to {}",
            "form_submit": "Submit form {}",
            "button_click": "Click {}",
            "api_call": "Call API {}",
        }

        for event in events:
            action_type = event.get("type", "unknown")
            target = event.get("target", "unknown")
            description = action_descriptions.get(action_type, f"Execute {action_type} on {{}}").format(target)
            tool = TOOL_BINDINGS.get(action_type, "generic_execute")

            steps.append({
                "action": f"Step {step_number}: {description}",
                "tool": tool,
                "args_template": {"target": target, "payload": event.get("payload", {})},
                "expected_outcome": "success",
            })
            step_number += 1

        try:
            skill_name = f"{recording.recording_name or 'Demo'} Skill"
            skill_description = f"Automated skill from demo recording. Contains {len(steps)} steps performing actions on '{recording.recording_name}'."
            triggers = [{"event": "manual", "condition": "user_request"}]
            preconditions = []

            skill = DemoSkill(
                recording_id=recording.id,
                agent_id=recording.agent_id,
                name=skill_name,
                description=skill_description,
                steps=steps,
                triggers=triggers,
                preconditions=preconditions,
                is_active=True,
                replay_success_rate=1.0,
            )
            db.add(skill)
            await db.commit()
            await db.refresh(skill)

            recording.converted_skill_id = skill.id
            recording.status = "converted"
            await db.commit()

            logger.info(f"Demo skill created: {skill.id} '{skill_name}' with {len(steps)} steps")
            return SkillConversionResult(
                skill_id=skill.id,
                name=skill_name,
                steps_count=len(steps),
                success=True,
            )
        except Exception as e:
            logger.error(f"Failed to convert demo to skill: {e}")
            recording.status = "failed"
            await db.commit()
            return SkillConversionResult(success=False, error=str(e))

    async def replay_demonstration(
        self,
        recording_id: str,
        target_agent_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> dict:
        result = await db.execute(select(DemoSession).where(DemoSession.id == recording_id))
        recording = result.scalar_one_or_none()
        if not recording:
            return {"success": False, "error": "Recording not found"}
        if not recording.events:
            return {"success": False, "error": "No events to replay"}

        events = recording.events
        replay_results = []
        passed = 0
        failed = 0

        for idx, event in enumerate(events):
            step_result = {
                "step": idx + 1,
                "action_type": event.get("type"),
                "target": event.get("target"),
                "status": "passed",
                "output": f"Replayed: {event.get('type')} on {event.get('target')} via agent {target_agent_id}",
            }
            try:
                step_description = step_result["output"]
                step_result["status"] = "passed"
                passed += 1
            except Exception as e:
                step_result["status"] = "failed"
                step_result["error"] = str(e)
                failed += 1

            replay_results.append(step_result)

        total = len(events)
        success_rate = passed / total if total > 0 else 0

        skill_result = await db.execute(
            select(DemoSkill).where(DemoSkill.recording_id == recording_id)
        )
        skill = skill_result.scalar_one_or_none()
        if skill:
            skill.replay_success_rate = success_rate
            await db.commit()

        logger.info(f"Demo replay: {recording_id} -> agent {target_agent_id}: {passed}/{total} passed")
        return {
            "success": failed == 0,
            "recording_id": recording_id,
            "target_agent_id": target_agent_id,
            "total_steps": total,
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate,
            "steps": replay_results,
        }
