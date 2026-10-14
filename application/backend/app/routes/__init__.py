"""Shared state and utilities for route modules"""
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address)

# Configure logging
logger = logging.getLogger(__name__)


class AppState:
    """Shared application state - avoids boolean-import-mutation issues"""
    startup_complete: bool = False
    llm_paused: bool = False


app_state = AppState()


def safe_error_response(e: Exception, context: str = "operation") -> str:
    """Log the full error but return a sanitized message to the client"""
    logger.error(f"{context} failed: {str(e)}", exc_info=True)
    return f"An error occurred during {context}. Please try again."
