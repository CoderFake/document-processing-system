import logging
import httpx
from typing import Dict, Any, Optional
from fastapi import HTTPException

from core.config import settings

logger = logging.getLogger(__name__)

async def send_to_user_service(
    method: str,
    endpoint: str,
    user_id: Optional[str] = None,
    json: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> httpx.Response:
    """
    Gửi yêu cầu đến service-user
    
    Args:
        method: Phương thức HTTP (GET, POST, PUT, DELETE)
        endpoint: Đường dẫn endpoint
        user_id: ID người dùng
        json: Dữ liệu JSON
        data: Dữ liệu form
        params: Tham số query
        
    Returns:
        Phản hồi từ service-user
    """
    url = f"{settings.USER_SERVICE_URL}{endpoint}"
    headers = {}
    
    if user_id:
        headers["X-User-ID"] = str(user_id)
    
    try:
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=json, data=data, params=params)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=headers, json=json, data=data, params=params)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"Phương thức không hỗ trợ: {method}")
                
        return response
    except httpx.HTTPError as e:
        logger.error(f"Lỗi khi gửi yêu cầu đến service-user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi giao tiếp với service-user: {str(e)}")
    except Exception as e:
        logger.error(f"Lỗi không xác định khi gửi yêu cầu đến service-user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}") 