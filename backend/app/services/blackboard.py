import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.core.redis import get_redis

logger = logging.getLogger("successcore.blackboard")

class BlackboardSession:
    """
    Manages the Multi-Agent Orchestration shared state using Redis.
    Agents can post hypotheses, validate each other, and the orchestrator can check for consensus.
    """
    
    PREFIX = "blackboard:"

    @classmethod
    async def create_session(cls, task_description: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new blackboard session for a complex multi-agent task."""
        r = await get_redis()
        session_id = uuid.uuid4().hex
        key = f"{cls.PREFIX}{session_id}"
        
        session_data = {
            "id": session_id,
            "task_description": task_description,
            "metadata": json.dumps(metadata or {}),
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "hypotheses": "[]"
        }
        
        if r:
            await r.hset(key, mapping=session_data)
            await r.expire(key, 86400) # Expire after 24h
        
        return session_id

    @classmethod
    async def post_hypothesis(cls, session_id: str, agent_id: str, hypothesis_data: Any) -> str:
        """An agent posts a hypothesis to the shared state."""
        r = await get_redis()
        if not r:
            return ""
            
        key = f"{cls.PREFIX}{session_id}"
        if not await r.exists(key):
            raise ValueError("Blackboard session does not exist")
            
        hypothesis_id = uuid.uuid4().hex
        hypothesis = {
            "id": hypothesis_id,
            "agent_id": agent_id,
            "data": hypothesis_data,
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "validations": []
        }
        
        raw_hypotheses = await r.hget(key, "hypotheses")
        hypotheses_list = json.loads(raw_hypotheses) if raw_hypotheses else []
        hypotheses_list.append(hypothesis)
        
        await r.hset(key, "hypotheses", json.dumps(hypotheses_list))
        return hypothesis_id

    @classmethod
    async def validate_hypothesis(
        cls, session_id: str, validating_agent_id: str, hypothesis_id: str, is_valid: bool, feedback: str
    ) -> bool:
        """An agent reviews and validates/rejects another agent's hypothesis."""
        r = await get_redis()
        if not r:
            return False
            
        key = f"{cls.PREFIX}{session_id}"
        raw_hypotheses = await r.hget(key, "hypotheses")
        if not raw_hypotheses:
            return False
            
        hypotheses_list = json.loads(raw_hypotheses)
        updated = False
        
        for hyp in hypotheses_list:
            if hyp["id"] == hypothesis_id:
                hyp["validations"].append({
                    "validating_agent_id": validating_agent_id,
                    "is_valid": is_valid,
                    "feedback": feedback,
                    "validated_at": datetime.now(timezone.utc).isoformat()
                })
                updated = True
                break
                
        if updated:
            await r.hset(key, "hypotheses", json.dumps(hypotheses_list))
            
        return updated

    @classmethod
    async def check_consensus(cls, session_id: str, required_validations: int = 1) -> Dict[str, Any]:
        """Check if any hypothesis has reached consensus."""
        r = await get_redis()
        if not r:
            return {"consensus_reached": False, "best_hypothesis": None}
            
        key = f"{cls.PREFIX}{session_id}"
        raw_hypotheses = await r.hget(key, "hypotheses")
        if not raw_hypotheses:
            return {"consensus_reached": False, "best_hypothesis": None}
            
        hypotheses_list = json.loads(raw_hypotheses)
        
        for hyp in hypotheses_list:
            validations = hyp.get("validations", [])
            positive_votes = sum(1 for v in validations if v.get("is_valid") is True)
            negative_votes = sum(1 for v in validations if v.get("is_valid") is False)
            
            if positive_votes >= required_validations and negative_votes == 0:
                return {"consensus_reached": True, "best_hypothesis": hyp}
                
        return {"consensus_reached": False, "best_hypothesis": None}

    @classmethod
    async def get_session_state(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the entire state of the blackboard."""
        r = await get_redis()
        if not r:
            return None
            
        key = f"{cls.PREFIX}{session_id}"
        state = await r.hgetall(key)
        if not state:
            return None
            
        return {
            "id": state.get(b"id", b"").decode("utf-8"),
            "task_description": state.get(b"task_description", b"").decode("utf-8"),
            "status": state.get(b"status", b"").decode("utf-8"),
            "hypotheses": json.loads(state.get(b"hypotheses", b"[]").decode("utf-8"))
        }
