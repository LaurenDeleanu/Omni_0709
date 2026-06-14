import pytest


@pytest.mark.asyncio
async def test_list_agents(async_client, auth_headers):
    response = await async_client.get(
        "/api/v1/agents",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_crew_execute_returns_200(async_client, auth_headers):
    response = await async_client.post(
        "/api/v1/agents/crew/execute",
        json={
            "task": "Generate a summary report for Q2 performance",
            "max_parallel": 2,
            "worker_timeout_seconds": 30,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
