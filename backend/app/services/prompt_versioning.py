import logging
import json
from datetime import datetime, timezone

logger = logging.getLogger("successcore.prompts")


class PromptVersionStore:
    def __init__(self):
        self._versions: dict = {}

    def save_version(self, agent_id: str, prompt_text: str, guardrails: str, tone: str, tools: str, changed_by: str) -> dict:
        if agent_id not in self._versions:
            self._versions[agent_id] = []
        version = {
            "version": len(self._versions[agent_id]) + 1,
            "agent_id": agent_id,
            "system_prompt": prompt_text,
            "guardrails": guardrails,
            "tone": tone,
            "tools": tools,
            "changed_by": changed_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._versions[agent_id].append(version)
        logger.info(f"Prompt version {version['version']} saved for agent {agent_id} by {changed_by}")
        return version

    def get_history(self, agent_id: str, limit: int = 20) -> list:
        versions = self._versions.get(agent_id, [])
        return versions[-limit:]

    def get_version(self, agent_id: str, version_num: int) -> dict | None:
        versions = self._versions.get(agent_id, [])
        for v in versions:
            if v["version"] == version_num:
                return v
        return None

    def rollback(self, agent_id: str, version_num: int, changed_by: str) -> dict | None:
        target = self.get_version(agent_id, version_num)
        if not target:
            return None
        return self.save_version(
            agent_id,
            target["system_prompt"],
            target["guardrails"],
            target["tone"],
            target["tools"],
            changed_by,
        )


_prompt_store = PromptVersionStore()


def get_prompt_store() -> PromptVersionStore:
    return _prompt_store
