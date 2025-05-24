from fastapi import Header, HTTPException, status

async def get_current_user_id_from_header(x_user_id: str = Header(None)) -> str:
    """
    Dependency để lấy user_id từ header X-User-ID.
    Raise HTTPException nếu header thiếu hoặc không hợp lệ.
    """
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-ID header is missing",
        )
    try:
        import uuid
        uuid.UUID(x_user_id)
        return x_user_id
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid X-User-ID header: must be a valid UUID",
        )
