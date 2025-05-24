from fastapi import Header, HTTPException, status
from typing import Optional
import uuid

async def get_current_user_id_from_header(x_user_id: Optional[str] = Header(None, alias="X-User-ID")) -> str:
    """
    Dependency để lấy user_id từ header X-User-ID và validate là UUID hợp lệ
    """
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-ID header is missing",
        )
    
    try:
        uuid_obj = uuid.UUID(x_user_id)
        return str(uuid_obj)
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid X-User-ID header: must be a valid UUID format",
        )