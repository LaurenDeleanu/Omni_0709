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

async def test_omni():
    token = generate_mock_token()
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "http://127.0.0.1:8000/api/v1/omni"
    
    print("Starting integration test for Omni Command Center...")
    
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # 1. Get Master Agent details (creates if not exists)
        print("\nFetching Omni Master config...")
        r = await client.get(f"{base_url}/master")
        print(f"Status: {r.status_code}")
        assert r.status_code == 200, f"Failed to fetch master config: {r.text}"
        data = r.json()
        print(f"Agent name: {data['agent']['name']}, Model: {data['agent']['aiModel']}")
        
        # 2. List codebase files
        print("\nListing root codebase files...")
        r = await client.get(f"{base_url}/files?action=list&path=.")
        print(f"Status: {r.status_code}")
        assert r.status_code == 200, f"Failed to list files: {r.text}"
        files_data = r.json()
        print(f"Found {len(files_data['files'])} files/folders in root.")
        
        # 3. Read specific file (e.g. backend/requirements.txt or test_http.py)
        print("\nReading test_http.py...")
        r = await client.get(f"{base_url}/files?action=read&path=backend/test_http.py")
        print(f"Status: {r.status_code}")
        assert r.status_code == 200, f"Failed to read file: {r.text}"
        read_data = r.json()
        assert "httpx" in read_data["content"]
        print("Read file content successfully validated!")

        # 4. Check git-status
        print("\nChecking git status...")
        r = await client.get(f"{base_url}/git-status")
        print(f"Status: {r.status_code}")
        assert r.status_code == 200, f"Failed to get git status: {r.text}"
        git_data = r.json()
        print(f"Git status returned {len(git_data['files'])} modified files.")
        
        # 5. Patch config
        print("\nConfiguring Omni Agent...")
        patch_payload = {
            "name": "Acme Omni Controller",
            "maxLoops": 12
        }
        r = await client.patch(f"{base_url}/master", json=patch_payload)
        print(f"Status: {r.status_code}")
        assert r.status_code == 200, f"Failed to patch config: {r.text}"
        
        # Confirm patch
        r = await client.get(f"{base_url}/master")
        assert r.json()["agent"]["name"] == "Acme Omni Controller"
        assert r.json()["agent"]["agentConfig"]["maxLoops"] == 12
        print("Config successfully updated and confirmed!")
        
        print("\nOmni Command Center integration test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_omni())
