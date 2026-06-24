import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.agent import Agent
from app.models.user import User
from app.services.agent_cost_tracker import (
    calculate_token_cost,
    apply_reseller_billing,
    record_budget_consumption
)
from app.services.agent_executor import execute_agent_run

def test_calculate_token_cost():
    # input: 1M tokens cost 0.15 USD, output: 1M tokens cost 0.60 USD
    # Test 100k input, 50k output
    cost = calculate_token_cost(100_000, 50_000)
    expected = (100_000 / 1_000_000 * 0.15) + (50_000 / 1_000_000 * 0.6)
    assert abs(cost - expected) < 1e-9

@pytest.mark.asyncio
async def test_reseller_billing_no_byok(db):
    # Create an agent and user
    agent = Agent(
        id="agent_reseller_1",
        name="Billing Agent",
        agent_type="finance",
        ai_model="gpt-4o-mini",
        agent_settings={}
    )
    user = User(
        id="user_reseller_1",
        email="reseller@example.com",
        full_name="Reseller User",
        is_active=True,
        current_debt=0.0
    )
    db.add(agent)
    db.add(user)
    await db.commit()

    # Apply reseller billing with NO BYOK (should add debt)
    with patch("app.services.llm_router.get_tenant_keys", new_callable=AsyncMock) as mock_keys:
        mock_keys.return_value = {}  # No tenant API keys
        await apply_reseller_billing(agent, db, 1.50, {"user_id": user.id})
        
        assert user.current_debt == 1.50

@pytest.mark.asyncio
async def test_reseller_billing_with_byok(db):
    agent = Agent(
        id="agent_reseller_2",
        name="BYOK Agent",
        agent_type="finance",
        ai_model="gpt-4o-mini",
        agent_settings={}
    )
    user = User(
        id="user_reseller_2",
        email="byok_user@example.com",
        full_name="BYOK User",
        is_active=True,
        current_debt=0.0
    )
    db.add(agent)
    db.add(user)
    await db.commit()

    # Apply reseller billing WITH BYOK (should NOT add debt)
    with patch("app.services.llm_router.get_tenant_keys", new_callable=AsyncMock) as mock_keys:
        mock_keys.return_value = {"openai_api_key": "sk-test-key"}
        await apply_reseller_billing(agent, db, 1.50, {"user_id": user.id})
        
        assert user.current_debt == 0.0

@pytest.mark.asyncio
async def test_record_budget_consumption(db):
    # Verify budget consumption runs and resolves non-fatally
    # Even if budget system throws an exception, it should catch it non-fatally
    with patch("app.services.agent_budget.record_cost", new_callable=AsyncMock) as mock_record:
        mock_record.side_effect = Exception("Budget DB down")
        # Should log warning but not raise
        await record_budget_consumption("agent_test_id", 0.05, db)
        mock_record.assert_called_once_with("agent_test_id", 0.05, db)

@pytest.mark.asyncio
@patch("app.services.agent_executor._execute_agent_run_inner", new_callable=AsyncMock)
async def test_execute_agent_run_success(mock_inner, db):
    mock_inner.return_value = {"status": "success", "response": "Hello World"}
    
    res = await execute_agent_run(
        db=db,
        agent_id="test_agent",
        input_payload={"user_id": "test_user"},
        trigger_source="manual"
    )
    assert res["status"] == "success"
    assert res["response"] == "Hello World"
