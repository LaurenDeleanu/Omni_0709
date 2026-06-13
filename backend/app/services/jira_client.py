import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("successcore.integrations.jira")

class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.auth = (email, api_token)

    async def _request(self, method: str, endpoint: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/3/{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method, 
                    url, 
                    json=json, 
                    auth=self.auth,
                    headers={"Accept": "application/json", "Content-Type": "application/json"}
                )
                response.raise_for_status()
                # 204 No Content won't return JSON
                if response.status_code != 204:
                    return response.json()
                return {}
            except Exception as e:
                logger.error(f"Jira API error on {method} {url}: {e}")
                raise

    async def create_ticket(self, project_key: str, summary: str, description: str, issue_type: str = "Task") -> str:
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }
                    ]
                },
                "issuetype": {"name": issue_type}
            }
        }
        res = await self._request("POST", "issue", json=payload)
        return res.get("key")

    async def add_comment(self, issue_key: str, comment: str) -> None:
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}]
                    }
                ]
            }
        }
        await self._request("POST", f"issue/{issue_key}/comment", json=payload)

    async def update_status(self, issue_key: str, transition_name: str) -> None:
        # 1. Get transitions
        transitions = await self._request("GET", f"issue/{issue_key}/transitions")
        transition_id = None
        for t in transitions.get("transitions", []):
            if t["name"].lower() == transition_name.lower():
                transition_id = t["id"]
                break
        
        if not transition_id:
            logger.warning(f"Jira transition {transition_name} not found for issue {issue_key}")
            return
            
        # 2. Execute transition
        payload = {"transition": {"id": transition_id}}
        await self._request("POST", f"issue/{issue_key}/transitions", json=payload)


async def push_ticket_to_jira(ticket_id: str, db):
    """
    Called asynchronously when an IT Ticket is created.
    """
    from sqlalchemy import select
    from app.models.it import ITTicket
    from app.models.tenant import Tenant
    
    # In a real setup, tenant ID should be resolved. Assuming we have some config or mock it here.
    # For now, we simulate the logic.
    res = await db.execute(select(ITTicket).where(ITTicket.id == ticket_id))
    ticket = res.scalar_one_or_none()
    if not ticket:
        return
        
    # Attempt to load Jira configuration from Tenant preferences/meta (or env)
    # Mocking config retrieval for prototype
    jira_url = "https://example.atlassian.net"
    jira_email = "admin@example.com"
    jira_token = "mock_token"
    jira_project = "IT"
    
    # In reality, check if config exists
    if not jira_url or not jira_token:
        return
        
    client = JiraClient(jira_url, jira_email, jira_token)
    try:
        # We wrap this in a try-except to avoid breaking the flow if we're using a mock URL
        # For prototype demonstration, we simulate success
        logger.info(f"Mock: Creating Jira ticket for IT ticket {ticket.title}")
        mock_jira_key = f"IT-{ticket.id[:4].upper()}"
        
        meta = ticket.ticket_meta or {}
        meta["jira_key"] = mock_jira_key
        ticket.ticket_meta = meta
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to push IT ticket {ticket_id} to Jira: {e}")
