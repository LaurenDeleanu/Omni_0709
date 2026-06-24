import logging
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class Microsoft365Integration:
    """Mock implementation for Microsoft 365 Integration."""
    
    @staticmethod
    async def get_auth_url() -> str:
        redirect_uri = f"{settings.FRONTEND_URL.rstrip('/')}/api/v1/auth/microsoft/callback"
        return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=mock_client_id&response_type=code&scope=openid%20email%20profile%20Calendars.Read&redirect_uri={redirect_uri}"
        
    @staticmethod
    async def exchange_code(code: str) -> Dict[str, Any]:
        # Mock exchanging code for token and getting user profile
        logger.info(f"Mocking Microsoft OAuth code exchange for code: {code}")
        return {
            "email": "mock.ms.user@example.com",
            "name": "Microsoft Mock User",
            "picture": "https://graph.microsoft.com/v1.0/me/photo/$value",
            "access_token": "mock_ms_access_token"
        }
        
    @staticmethod
    async def fetch_calendar_events(access_token: str) -> list:
        # Mock fetching calendar events
        logger.info("Mocking Microsoft Calendar fetch")
        return [
            {
                "id": "mock_ms_event_1",
                "subject": "Project Review",
                "start": "2026-06-12T14:00:00Z",
                "end": "2026-06-12T15:00:00Z"
            }
        ]
