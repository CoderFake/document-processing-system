import httpx
from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional, Union
import json
import io



class ServiceClient:
    """
    Client để giao tiếp với các microservice khác.
    """

    def __init__(self, base_url: str, timeout: int = 60):
        """
        Khởi tạo client với URL cơ sở của service.

        Args:
            base_url: URL cơ sở của service
            timeout: Thời gian timeout cho các request (giây)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Gửi GET request đến service.

        Args:
            endpoint: Endpoint cần gọi (không bao gồm base_url)
            params: Các tham số query string
            headers: Optional dictionary chứa các header cho request.

        Returns:
            Phản hồi từ service dưới dạng dict
        """
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)

                if response.status_code >= 400:
                    error_detail = response.json().get('detail', 'Lỗi không xác định') if response.headers.get(
                        'content-type') == 'application/json' else response.text
                    raise HTTPException(status_code=response.status_code, detail=error_detail)

                return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Lỗi kết nối đến service: {str(exc)}")

    async def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Gửi POST request với dữ liệu JSON đến service.

        Args:
            endpoint: Endpoint cần gọi (không bao gồm base_url)
            json_data: Dữ liệu JSON để gửi trong body
            headers: Optional dictionary chứa các header cho request.

        Returns:
            Phản hồi từ service dưới dạng dict
        """
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=json_data, headers=headers)

                if response.status_code >= 400:
                    error_detail = response.json().get('detail', 'Lỗi không xác định') if response.headers.get(
                        'content-type') == 'application/json' else response.text
                    raise HTTPException(status_code=response.status_code, detail=error_detail)

                return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Lỗi kết nối đến service: {str(exc)}")

    async def delete(self, endpoint: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Gửi DELETE request đến service.

        Args:
            endpoint: Endpoint cần gọi (không bao gồm base_url)
            headers: Optional dictionary chứa các header cho request.

        Returns:
            Phản hồi từ service dưới dạng dict
        """
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code >= 400:
                    error_detail = response.json().get('detail', 'Lỗi không xác định') if response.headers.get(
                        'content-type') == 'application/json' else response.text
                    raise HTTPException(status_code=response.status_code, detail=error_detail)

                return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Lỗi kết nối đến service: {str(exc)}")

    async def upload_file(self, endpoint: str, file: UploadFile, data: Optional[Dict[str, str]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[
        str, Any]:
        """
        Tải lên một file đến service.

        Args:
            endpoint: Endpoint cần gọi (không bao gồm base_url)
            file: File cần tải lên
            data: Dữ liệu form bổ sung
            headers: Optional dictionary chứa các header cho request.

        Returns:
            Phản hồi từ service dưới dạng dict
        """
        url = f"{self.base_url}{endpoint}"

        try:
            await file.seek(0)
            file_content = await file.read()

            files = {"file": (file.filename, file_content, file.content_type)}

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, files=files, data=data, headers=headers)

                if response.status_code >= 400:
                    error_detail = response.json().get('detail', 'Lỗi không xác định') if response.headers.get(
                        'content-type') == 'application/json' else response.text
                    raise HTTPException(status_code=response.status_code, detail=error_detail)

                return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Lỗi kết nối đến service: {str(exc)}")

    async def upload_files(self, endpoint: str, files: Union[List[UploadFile], Dict[str, UploadFile]],
                           data: Optional[Dict[str, str]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Tải lên nhiều file đến service.

        Args:
            endpoint: Endpoint cần gọi (không bao gồm base_url)
            files: List hoặc Dict các file cần tải lên
            data: Dữ liệu form bổ sung
            headers: Optional dictionary chứa các header cho request.

        Returns:
            Phản hồi từ service dưới dạng dict
        """
        url = f"{self.base_url}{endpoint}"

        try:
            files_to_upload = {}

            if isinstance(files, list):
                for i, file_item in enumerate(files):
                    await file_item.seek(0)
                    file_content = await file_item.read()
                    files_to_upload[f"file_{i}"] = (file_item.filename, file_content, file_item.content_type)
            else:
                for key, file_item in files.items():
                    if file_item is not None:  
                        await file_item.seek(0)
                        file_content = await file_item.read()
                        files_to_upload[key] = (file_item.filename, file_content, file_item.content_type)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, files=files_to_upload, data=data, headers=headers)

                if response.status_code >= 400:
                    error_detail = response.json().get('detail', 'Lỗi không xác định') if response.headers.get(
                        'content-type') == 'application/json' else response.text
                    raise HTTPException(status_code=response.status_code, detail=error_detail)

                return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Lỗi kết nối đến service: {str(exc)}")

    async def get_file(self, endpoint: str, headers: Optional[Dict[str, str]] = None) -> StreamingResponse:
        """
        Lấy file từ service và trả về dưới dạng StreamingResponse.

        Args:
            endpoint: Endpoint cần gọi (không bao gồm base_url)
            headers: Optional dictionary chứa các header cho request.

        Returns:
            StreamingResponse chứa nội dung file
        """
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code >= 400:
                    error_detail = response.json().get('detail', 'Lỗi không xác định') if response.headers.get(
                        'content-type') == 'application/json' else response.text
                    raise HTTPException(status_code=response.status_code, detail=error_detail)

                content_type = response.headers.get("content-type", "application/octet-stream")
                content_disposition = response.headers.get("content-disposition", "")

                return StreamingResponse(
                    io.BytesIO(response.content),
                    media_type=content_type,
                    headers={"Content-Disposition": content_disposition}
                )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Lỗi kết nối đến service: {str(exc)}")

    async def post_form(self, endpoint: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Gửi POST request với dữ liệu form đến service.

        Args:
            endpoint: Endpoint cần gọi (không bao gồm base_url)
            data: Dữ liệu form để gửi
            headers: Optional dictionary chứa các header cho request.

        Returns:
            Phản hồi từ service dưới dạng dict
        """
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, data=data, headers=headers)

                if response.status_code >= 400:
                    error_detail = response.json().get('detail', 'Lỗi không xác định') if response.headers.get(
                        'content-type') == 'application/json' else response.text
                    raise HTTPException(status_code=response.status_code, detail=error_detail)

                return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Lỗi kết nối đến service: {str(exc)}")