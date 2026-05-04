"""
Session Store Strategy
Abstracts ADK SessionService backend (InMemory vs Redis).
"""
import os
from google.adk.runners.services.session import SessionService, InMemorySessionService

class SessionServiceStrategy:
    """Strategy interface for providing ADK SessionService."""
    
    def get_service(self) -> SessionService:
        # Defaults to InMemorySessionService
        return InMemorySessionService()

def get_session_service() -> SessionService:
    """Factory to get the configured session service."""
    strategy_name = os.getenv("SESSION_STRATEGY", "in_memory").lower()
    
    # Example logic for expanding to Redis later
    if strategy_name == "redis":
        # return RedisSessionAdapter(os.getenv("REDIS_URL")).get_service()
        pass
        
    return SessionServiceStrategy().get_service()
