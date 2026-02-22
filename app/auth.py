import os
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(api_key: str = Security(_api_key_header)) -> str:
    expected = os.getenv("GDEV_API_TOKEN", "dev-secret-token")
    if api_key and api_key == expected:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key. Provide it via the X-API-Key header.",
    )
