import httpx
from fastapi import HTTPException
from typing import Dict, Any, Optional
import io
import logging

logger = logging.getLogger(__name__)

class ServiceClient:
    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    async def download_file_content(
        self, 
        base_url: str, 
        document_id: str,
        user_id: str
    ) -> bytes:
        """
        Tải nội dung file từ một service khác.
        Gọi đến endpoint dạng /documents/download/{document_id}?user_id={user_id}
        """
        url = f"{base_url.rstrip('/')}/documents/download/{document_id}?user_id={user_id}"
        logger.debug(f"Downloading file content from: {url}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, follow_redirects=True)

                if response.status_code == 200:
                    logger.debug(f"Successfully downloaded file {document_id} for user {user_id} from {base_url}")
                    return response.content
                else:
                    error_detail = "Unknown error"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", response.text)
                    except Exception:
                        error_detail = response.text
                    
                    logger.error(f"Error downloading file {document_id} from {base_url}. Status: {response.status_code}, Detail: {error_detail}")
                    raise HTTPException(
                        status_code=response.status_code, 
                        detail=f"Could not download file from {base_url}: {error_detail}"
                    )
        except httpx.RequestError as exc:
            logger.error(f"RequestError while downloading file {document_id} from {base_url}: {str(exc)}")
            raise HTTPException(status_code=503, detail=f"Service unavailable at {base_url}: {str(exc)}")
        except Exception as e:
            logger.error(f"Unexpected error downloading file {document_id} from {base_url}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error communicating with {base_url}: {str(e)}") 