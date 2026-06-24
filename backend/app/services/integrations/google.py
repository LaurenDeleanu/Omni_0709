import logging
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class GoogleWorkspaceIntegration:
    """Mock implementation for Google Workspace Integration."""
    
    @staticmethod
    async def get_auth_url() -> str:
        redirect_uri = f"{settings.FRONTEND_URL.rstrip('/')}/api/v1/auth/google/callback"
        return f"https://accounts.google.com/o/oauth2/v2/auth?client_id=mock_client_id&response_type=code&scope=openid%20email%20profile%20https://www.googleapis.com/auth/calendar.readonly&redirect_uri={redirect_uri}"
        
    @staticmethod
    async def exchange_code(code: str) -> Dict[str, Any]:
        # Mock exchanging code for token and getting user profile
        logger.info(f"Mocking Google OAuth code exchange for code: {code}")
        return {
            "email": "mock.google.user@example.com",
            "name": "Google Mock User",
            "picture": "https://lh3.googleusercontent.com/a/mock",
            "access_token": "mock_google_access_token"
        }
        
    @staticmethod
    async def fetch_calendar_events(access_token: str) -> list:
        # Mock fetching calendar events
        logger.info("Mocking Google Calendar fetch")
        return [
            {
                "id": "mock_event_1",
                "summary": "Team Sync",
                "start": "2026-06-12T10:00:00Z",
                "end": "2026-06-12T11:00:00Z"
            }
        ]
