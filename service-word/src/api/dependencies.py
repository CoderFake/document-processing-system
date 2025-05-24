from fastapi import Header, HTTPException, status
from typing import Optional

async def get_current_user_id_from_header(x_user_id: Optional[str] = Header(None, alias="X-User-ID")) -> int:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-ID header is missing",
        )
    try:
        user_id = int(x_user_id)
        if user_id <= 0: 
             raise ValueError("User ID must be a positive integer")
        return user_id
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid X-User-ID header: {str(e)}",
        ) 