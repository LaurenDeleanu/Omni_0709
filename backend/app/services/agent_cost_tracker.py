import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.agent import Agent
from app.models.user import User

logger = logging.getLogger("successcore.agent_cost_tracker")

PRICE_INPUT_1M = 0.150  # USD
PRICE_OUTPUT_1M = 0.600 # USD

def calculate_token_cost(input_tokens: int, output_tokens: int) -> float:
    """
    Calculates estimated cost based on token counts.
    """
    cost_in = (input_tokens / 1_000_000) * PRICE_INPUT_1M
    cost_out = (output_tokens / 1_000_000) * PRICE_OUTPUT_1M
    return cost_in + cost_out

async def apply_reseller_billing(
    agent: Agent,
    db: AsyncSession,
    cost_usd: float,
    input_payload: Dict[str, Any]
) -> None:
    """
    If the tenant is not using their own API keys (BYOK), charge the cost to the user's debt balance.
    """
    try:
        from app.services.llm_router import get_tenant_keys
        tenant_keys = await get_tenant_keys(agent, db)
        
        # Determine model provider
        model_name = agent.ai_model.lower()
        provider = "openai"
        if "claude" in model_name or "anthropic" in model_name:
            provider = "anthropic"
        elif "grok" in model_name:
            provider = "xai"
        elif "/" in model_name or "openrouter" in model_name:
            provider = "openrouter"
        elif "gemini" in model_name:
            provider = "gemini"
            
        byok_active = False
        if provider == "openai" and tenant_keys.get("openai_api_key"):
            byok_active = True
        elif provider == "openrouter" and tenant_keys.get("openrouter_api_key"):
            byok_active = True
        elif provider == "gemini" and tenant_keys.get("gemini_api_key"):
            byok_active = True
        elif provider == "anthropic" and tenant_keys.get("anthropic_api_key"):
            byok_active = True
        elif provider == "xai" and tenant_keys.get("grok_api_key"):
            byok_active = True
            
        # Also check if keys are configured at the agent level
        if agent.agent_settings:
            if provider == "openai" and agent.agent_settings.get("openai_api_key"):
                byok_active = True
            elif provider == "openrouter" and agent.agent_settings.get("openrouter_api_key"):
                byok_active = True
            elif provider == "gemini" and agent.agent_settings.get("gemini_api_key"):
                byok_active = True
            elif provider == "anthropic" and agent.agent_settings.get("anthropic_api_key"):
                byok_active = True
            elif provider == "xai" and agent.agent_settings.get("grok_api_key"):
                byok_active = True
                
        if not byok_active:
            user_id = input_payload.get("user_id")
            if user_id:
                user_res = await db.execute(
                    select(User).where((User.id == user_id) | (User.email == user_id))
                )
                user = user_res.scalar_one_or_none()
                if user:
                    user.current_debt += cost_usd
    except Exception as e:
        logger.error(f"Error in reseller billing cost hook: {e}")

async def record_budget_consumption(agent_id: str, cost_usd: float, db: AsyncSession) -> None:
    """
    Update the agent's running budget usage tracking.
    """
    try:
        from app.services.agent_budget import record_cost
        await record_cost(agent_id, cost_usd, db)
    except Exception as e:
        logger.warning(f"Budget record failed (non-fatal): {e}")
