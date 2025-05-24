from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Dict, Any, Optional
from core.config import settings
from utils.client import ServiceClient
from api.v1.endpoints.auth import get_current_user

router = APIRouter()

user_service = ServiceClient(settings.USER_SERVICE_URL)

@router.get("/stats", summary="Lấy thống kê tài liệu")
async def get_stats(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy thống kê số lượng các loại tài liệu trong hệ thống.
    """
    try:
        response = await user_service.get("/stats", params={"user_id": current_user["id"]})
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Không thể lấy số liệu thống kê: {str(e)}"
        )

@router.get("/recent-documents", summary="Lấy tài liệu gần đây")
async def get_recent_documents(
    limit: int = Query(5, description="Số lượng tài liệu muốn lấy"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy danh sách tài liệu gần đây của người dùng hiện tại.
    """
    try:
        response = await user_service.get("/user/recent-documents", 
                                        params={
                                            "limit": limit,
                                            "user_id": current_user["id"]
                                        })
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Không thể lấy danh sách tài liệu: {str(e)}"
        ) 