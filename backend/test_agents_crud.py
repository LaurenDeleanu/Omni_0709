import asyncio
import os
import sys
import httpx
from jose import jwt
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.core.config import settings

def generate_mock_token():
    payload = {
        "sub": "auth0|mock_admin_123",
        "tenant_id": "acme_corp",
        "roles": ["hr_admin"],
        "email": "admin@acme.com"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

async def test_crud():
    token = generate_mock_token()
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "http://127.0.0.1:8000/api/v1/agents"
    
    print("Starting integration test for Agent Studio...")
    
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # 1. Create Agent
        payload = {
            "name": "Integration Test Agent",
            "avatar": "🤖",
            "agentType": "conversational",
            "aiModel": "gemini-2.5-flash",
            "aiSystemPrompt": "You are a test assistant. Answer with 'Beep Boop'.",
            "aiTemperature": 0.5,
            "aiTone": "Robot",
            "agentSettings": {
                "gemini_api_key": "mock_api_key"
            },
            "config": {
                "max_loops": 5,
                "max_tokens_per_run": 10000
            }
        }
        
        print("\nCreating agent...")
        r = await client.post(base_url, json=payload)
        print(f"Status: {r.status_code}")
        assert r.status_code == 201, f"Failed to create agent: {r.text}"
        data = r.json()
        agent_id = data["id"]
        print(f"Agent created successfully! ID: {agent_id}")
        
        # 2. Get Agent details
        print(f"\nRetrieving agent details for {agent_id}...")
        r = await client.get(f"{base_url}/{agent_id}")
        print(f"Status: {r.status_code}")
        assert r.status_code == 200, f"Failed to retrieve agent: {r.text}"
        agent_data = r.json()
        print(f"Retrieved: {agent_data['name']}, Tone: {agent_data['aiTone']}, API key: {agent_data['agentSettings'].get('gemini_api_key')}")
        
        # 3. Update Agent
        print(f"\nUpdating agent details...")
        update_payload = {
            "name": "Updated Test Agent",
            "aiTone": "Hyper-Robot"
        }
        r = await client.patch(f"{base_url}/{agent_id}", json=update_payload)
        print(f"Status: {r.status_code}")
        assert r.status_code == 200, f"Failed to update agent: {r.text}"
        
        # Confirm update
        r = await client.get(f"{base_url}/{agent_id}")
        assert r.json()["name"] == "Updated Test Agent"
        print("Agent details updated and confirmed!")
        
        # 4. List Agents
        print("\nListing all agents...")
        r = await client.get(base_url)
        print(f"Status: {r.status_code}")
        assert r.status_code == 200
        agents_list = r.json()
        print(f"Found {len(agents_list)} agents.")
        
        # 5. Run simulation (chat)
        # We use a mock LLM key but let's test if the execution route resolves and triggers correctly
        print("\nSimulating agent run...")
        run_payload = {
            "message": "Hello, who are you?"
        }
        r = await client.post(f"{base_url}/{agent_id}/run", json=run_payload)
        print(f"Status: {r.status_code}")
        # Note: Since the API key is "mock_api_key", it might fail in the real LLM call.
        # But we want to see if it routes through execute_agent_run and handles the error gracefully.
        print(f"Response: {r.text}")
        
        # 6. Delete Agent
        print(f"\nDeleting agent {agent_id}...")
        r = await client.delete(f"{base_url}/{agent_id}")
        print(f"Status: {r.status_code}")
        assert r.status_code == 200, f"Failed to delete agent: {r.text}"
        
        # Verify deletion
        r = await client.get(f"{base_url}/{agent_id}")
        assert r.status_code == 404
        print("Agent deleted and verified!")
        
        print("\nIntegration test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_crud())
