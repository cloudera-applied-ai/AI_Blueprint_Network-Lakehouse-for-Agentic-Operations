"""API Key authentication dependency"""
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from .config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str = Security(api_key_header)):
    """Validate API key from X-API-Key header. Returns 401 if missing or invalid."""
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key. Include X-API-Key header.")
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return api_key
