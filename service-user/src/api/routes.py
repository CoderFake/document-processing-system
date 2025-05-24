from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Path
from typing import List, Dict, Any, Optional
from fastapi.security import OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import PyJWTError
import logging
import json

from application.services import UserService, AuthService, DocumentService, DocumentCategoryService
from application.dto import UserCreateDTO, UserUpdateDTO, UserRegisterDTO, TokenResponseDTO
from api.dependencies import get_user_service, get_current_user, get_auth_service, get_document_service, get_document_category_service, get_optional_current_user
from domain.models import User, Document, DocumentCategory
from application.security import create_access_token
from core.config import settings

router = APIRouter()

@router.post("/auth/register", response_model=UserCreateDTO, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def register(
    user_data: UserRegisterDTO,
    user_service: UserService = Depends(get_user_service)
):
    """
    Đăng ký người dùng mới.
    """
    try:
        create_data = UserCreateDTO(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            is_active=True,
            is_verified=False
        )
        user = await user_service.create_user(create_data)
        return create_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/auth/login", response_model=TokenResponseDTO, tags=["auth"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Đăng nhập và lấy token.
    """
    result = await user_service.authenticate_user(form_data.username, form_data.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_type": result["token_type"],
        "expires_in": 3600
    }

@router.post("/auth/validate-token", tags=["auth"])
async def validate_token(
    token: Dict[str, str],
    user_service: UserService = Depends(get_user_service)
):
    """
    Xác thực token và trả về thông tin người dùng.
    """
    try:
        token_str = token.get("token")
        if not token_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is required",
            )
       
        try:
            payload = jwt.decode(
                token_str,
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
        except PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/auth/refresh-token", response_model=TokenResponseDTO, tags=["auth"])
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Làm mới token JWT bằng refresh token.
    """
    try:
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required",
            )
            
        token_data = await auth_service.verify_refresh_token(refresh_token)
        user_id = token_data.user_id
        
        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        access_token = create_access_token(user)
        new_refresh_token = await auth_service.create_refresh_token(user_id)
        
        await auth_service.revoke_refresh_token(refresh_token)
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": 3600
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )

@router.post("/auth/logout", tags=["auth"])
async def logout(
    refresh_token: Optional[str] = Body(None, embed=True),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Đăng xuất người dùng bằng cách thu hồi refresh token.
    """
    try:
        if not refresh_token:
            return {"detail": "Successfully logged out"}
            
        success = await auth_service.revoke_refresh_token(refresh_token)
        if not success:
            return {"detail": "Successfully logged out"}
        return {"detail": "Successfully logged out"}
    except Exception as e:
        return {"detail": "Successfully logged out"}

@router.get("/users", tags=["users"])
async def get_users(
    skip: int = 0, 
    limit: int = 100,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy danh sách người dùng.
    """
    return await user_service.get_users(skip=skip, limit=limit)

@router.get("/users/{user_id}", tags=["users"])
async def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thông tin người dùng theo ID.
    """
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user

@router.post("/users", tags=["users"], status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateDTO,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    """
    Tạo người dùng mới.
    """
    return await user_service.create_user(user_data)

@router.put("/users/{user_id}", tags=["users"])
async def update_user(
    user_id: str,
    user_data: UserUpdateDTO,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    """
    Cập nhật thông tin người dùng.
    """
    user = await user_service.update_user(user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user

@router.delete("/users/{user_id}", tags=["users"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    """
    Xóa người dùng.
    """
    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return None

@router.get("/me", tags=["users"])
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thông tin người dùng hiện tại.
    """
    return current_user

@router.get("/stats", tags=["stats"])
async def get_stats(
    user_service: UserService = Depends(get_user_service),
    user_id: Optional[str] = Query(None, description="ID của người dùng để lọc thống kê"),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Lấy thống kê số lượng tài liệu trong hệ thống.
    Nếu cung cấp user_id, chỉ thống kê tài liệu của người dùng đó.
    Nếu không cung cấp user_id nhưng có current_user, sẽ dùng ID của current_user.
    """
    logger = logging.getLogger(__name__)
    try:
        import httpx
        from core.config import settings

        logger.info(f"PDF_SERVICE_URL: {settings.PDF_SERVICE_URL}")
        logger.info(f"WORD_SERVICE_URL: {settings.WORD_SERVICE_URL}")
        logger.info(f"EXCEL_SERVICE_URL: {settings.EXCEL_SERVICE_URL}")
        
        # Nếu không có user_id nhưng có current_user, sử dụng id của current_user
        if user_id is None and current_user is not None:
            user_id = current_user.id
            
        if user_id is not None:
            logger.info(f"Lấy thống kê cho user ID: {user_id}")
        else:
            logger.warning("Không có user_id để lọc, có thể sẽ không hiển thị tài liệu nào")
        
        total_documents = 0
        pdf_count = 0
        word_count = 0
        excel_count = 0
        
        success = False
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                pdf_api_path = f"{settings.PDF_SERVICE_URL}/documents"
                params = {"limit": 1000}
                if user_id is not None:
                    params["user_id"] = user_id
                    
                logger.info(f"Đang gọi API PDF documents từ {pdf_api_path} với params: {params}")
                pdf_response = await client.get(pdf_api_path, params=params)
                if pdf_response.status_code == 200:
                    pdf_data = pdf_response.json()
                    pdf_docs = pdf_data.get("items", [])
                    pdf_count = len(pdf_docs)
                    total_documents += pdf_count
                    success = True
                    logger.info(f"Nhận được PDF count: {pdf_count}")
                else:
                    logger.warning(f"PDF API trả về status code: {pdf_response.status_code}")
            except Exception as e:
                logger.error(f"Lỗi khi gọi PDF documents: {str(e)}")
            
            try:
                word_api_path = f"{settings.WORD_SERVICE_URL}/documents"
                params = {"limit": 1000}
                if user_id is not None:
                    params["user_id"] = user_id
                    
                logger.info(f"Đang gọi API Word documents từ {word_api_path} với params: {params}")
                word_response = await client.get(word_api_path, params=params)
                if word_response.status_code == 200:
                    word_data = word_response.json()
                    word_docs = word_data.get("items", [])
                    word_count = len(word_docs)
                    total_documents += word_count
                    success = True
                    logger.info(f"Nhận được Word count: {word_count}")
                else:
                    logger.warning(f"Word API trả về status code: {word_response.status_code}")
            except Exception as e:
                logger.error(f"Lỗi khi gọi Word documents: {str(e)}")
            
            try:
                excel_api_path = f"{settings.EXCEL_SERVICE_URL}/documents"
                params = {"limit": 1000}
                if user_id is not None:
                    params["user_id"] = user_id
                    
                logger.info(f"Đang gọi API Excel documents từ {excel_api_path} với params: {params}")
                excel_response = await client.get(excel_api_path, params=params)
                if excel_response.status_code == 200:
                    excel_data = excel_response.json()
                    excel_docs = excel_data.get("items", [])
                    excel_count = len(excel_docs)
                    total_documents += excel_count
                    success = True
                    logger.info(f"Nhận được Excel count: {excel_count}")
                else:
                    logger.warning(f"Excel API trả về status code: {excel_response.status_code}")
            except Exception as e:
                logger.error(f"Lỗi khi gọi Excel documents: {str(e)}")
        
        logger.info(f"Tổng cộng {total_documents} tài liệu ({pdf_count} PDF, {word_count} Word, {excel_count} Excel)")
        return {
            "totalDocuments": total_documents,
            "pdfCount": pdf_count,
            "wordCount": word_count,
            "excelCount": excel_count
        }
    
    except Exception as e:
        logger.error(f"Lỗi khi lấy thống kê tài liệu: {str(e)}")
        return {
            "totalDocuments": 0,
            "pdfCount": 0,
            "wordCount": 0,
            "excelCount": 0
        }

@router.get("/recent-documents", tags=["documents"])
async def get_user_recent_documents(
    limit: int = Query(5, description="Số lượng tài liệu muốn lấy"),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Lấy danh sách tài liệu gần đây của người dùng hiện tại.
    """
    logger = logging.getLogger(__name__)
    try:
    

        import httpx
        from core.config import settings
        
       
        logger.info(f"PDF_SERVICE_URL: {settings.PDF_SERVICE_URL}")
        logger.info(f"WORD_SERVICE_URL: {settings.WORD_SERVICE_URL}")
        logger.info(f"EXCEL_SERVICE_URL: {settings.EXCEL_SERVICE_URL}")
        
        user_id = current_user.id
        logger.info(f"Lấy tài liệu gần đây cho user ID: {user_id}")
        
        combined_documents = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                pdf_api_path = f"{settings.PDF_SERVICE_URL}/documents"
                logger.info(f"Đang gọi API PDF documents từ {pdf_api_path}")
                pdf_response = await client.get(pdf_api_path, 
                                          params={"limit": limit, "sort": "created_at:desc", "user_id": user_id})
                
                if pdf_response.status_code == 200:
                    pdf_data = pdf_response.json()
                    pdf_docs = pdf_data.get("items", [])
                    logger.info(f"Nhận được {len(pdf_docs)} tài liệu PDF")
                    for doc in pdf_docs:
                        doc["type"] = "pdf"
                        combined_documents.append(doc)
                else:
                    logger.warning(f"PDF API trả về status code: {pdf_response.status_code}")
            except Exception as e:
                logger.error(f"Lỗi khi gọi PDF service: {str(e)}")
            
            try:
                word_api_path = f"{settings.WORD_SERVICE_URL}/documents"
                logger.info(f"Đang gọi API Word documents từ {word_api_path}")
                word_response = await client.get(word_api_path, 
                                           params={"limit": limit, "sort": "created_at:desc", "user_id": user_id})
                
                if word_response.status_code == 200:
                    word_data = word_response.json()
                    word_docs = word_data.get("items", [])
                    logger.info(f"Nhận được {len(word_docs)} tài liệu Word")
                    for doc in word_docs:
                        doc["type"] = "word"
                        combined_documents.append(doc)
                else:
                    logger.warning(f"Word API trả về status code: {word_response.status_code}")
            except Exception as e:
                logger.error(f"Lỗi khi gọi Word service: {str(e)}")
                
            
            try:
                excel_api_path = f"{settings.EXCEL_SERVICE_URL}/documents"
                logger.info(f"Đang gọi API Excel documents từ {excel_api_path}")
                excel_response = await client.get(excel_api_path, 
                                            params={"limit": limit, "sort": "created_at:desc", "user_id": user_id})
                
                if excel_response.status_code == 200:
                    excel_data = excel_response.json()
                    excel_docs = excel_data.get("items", [])
                    logger.info(f"Nhận được {len(excel_docs)} tài liệu Excel")
                    for doc in excel_docs:
                        doc["type"] = "excel"
                        combined_documents.append(doc)
                else:
                    logger.warning(f"Excel API trả về status code: {excel_response.status_code}")
            except Exception as e:
                logger.error(f"Lỗi khi gọi Excel service: {str(e)}")
            
            if combined_documents:
                from datetime import datetime
                combined_documents.sort(
                    key=lambda x: datetime.fromisoformat(x.get("created_at", "").replace("Z", "+00:00")), 
                    reverse=True
                )
                
                logger.info(f"Tổng cộng {len(combined_documents)} tài liệu")
                
                return combined_documents[:limit]
            else:
                logger.warning("Không nhận được tài liệu nào từ các service, trả về mảng rỗng")
                return []
            
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách tài liệu gần đây: {str(e)}")
        return []

# --- Routes cho Documents ---

@router.post("/documents", response_model=Dict[str, Any])
async def create_document(
    document_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Tạo tài liệu mới.
    """
    document = await document_service.create_document(current_user.id, document_data)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tạo tài liệu"
        )
    
    result = document.__dict__.copy()
    if hasattr(document, "metadata") and document.metadata:
        try:
            result["metadata"] = json.loads(document.metadata)
        except:
            pass
            
    return result


@router.get("/documents", response_model=Dict[str, Any])
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    file_type: Optional[str] = None,
    service_name: Optional[str] = None,
    category_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Lấy danh sách tài liệu của người dùng hiện tại.
    """
    documents = await document_service.get_user_documents(
        current_user.id, skip, limit, file_type, service_name, category_id
    )
    total = await document_service.count_user_documents(
        current_user.id, file_type, service_name, category_id
    )
    
    items = []
    for doc in documents:
        item = doc.__dict__.copy()
        if hasattr(doc, "metadata") and doc.metadata:
            try:
                item["metadata"] = json.loads(doc.metadata)
            except:
                pass
        items.append(item)
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/documents/{document_id}", response_model=Dict[str, Any])
async def get_document(
    document_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Lấy thông tin chi tiết của tài liệu.
    """
    document = await document_service.get_document_by_id(document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tài liệu không tồn tại hoặc bạn không có quyền truy cập"
        )
    
    result = document.__dict__.copy()
    if hasattr(document, "metadata") and document.metadata:
        try:
            result["metadata"] = json.loads(document.metadata)
        except:
            pass
            
    return result


@router.get("/documents/storage/{storage_id}", response_model=Dict[str, Any])
async def get_document_by_storage_id(
    storage_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Lấy thông tin chi tiết của tài liệu theo ID lưu trữ.
    """
    document = await document_service.get_document_by_storage_id(storage_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tài liệu không tồn tại hoặc bạn không có quyền truy cập"
        )
    
    result = document.__dict__.copy()
    if hasattr(document, "metadata") and document.metadata:
        try:
            result["metadata"] = json.loads(document.metadata)
        except:
            pass
            
    return result


@router.put("/documents/{document_id}", response_model=Dict[str, Any])
async def update_document(
    document_id: str = Path(...),
    document_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Cập nhật thông tin tài liệu.
    """
    document = await document_service.update_document(document_id, document_data, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tài liệu không tồn tại hoặc bạn không có quyền cập nhật"
        )
    
    result = document.__dict__.copy()
    if hasattr(document, "metadata") and document.metadata:
        try:
            result["metadata"] = json.loads(document.metadata)
        except:
            pass
            
    return result


@router.delete("/documents/{document_id}", response_model=Dict[str, Any])
async def delete_document(
    document_id: str = Path(...),
    hard_delete: bool = False,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Xóa tài liệu.
    """
    success = await document_service.delete_document(document_id, current_user.id, hard_delete)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tài liệu không tồn tại hoặc bạn không có quyền xóa"
        )
    
    return {"success": True, "message": "Tài liệu đã được xóa thành công"}


# --- Routes cho Document Categories ---

@router.post("/document-categories", response_model=Dict[str, Any])
async def create_document_category(
    category_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    category_service: DocumentCategoryService = Depends(get_document_category_service)
):
    """
    Tạo danh mục tài liệu mới.
    """
    category = await category_service.create_category(category_data)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tạo danh mục tài liệu"
        )
    
    return category.__dict__


@router.get("/document-categories", response_model=Dict[str, Any])
async def get_document_categories(
    skip: int = 0,
    limit: int = 100,
    category_service: DocumentCategoryService = Depends(get_document_category_service)
):
    """
    Lấy danh sách danh mục tài liệu.
    """
    categories = await category_service.get_all_categories(skip, limit)
    total = await category_service.count_categories()
    
    return {
        "items": [category.__dict__ for category in categories],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/document-categories/{category_id}", response_model=Dict[str, Any])
async def get_document_category(
    category_id: int = Path(...),
    category_service: DocumentCategoryService = Depends(get_document_category_service)
):
    """
    Lấy thông tin chi tiết của danh mục tài liệu.
    """
    category = await category_service.get_category_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Danh mục tài liệu không tồn tại"
        )
    
    return category.__dict__


@router.put("/document-categories/{category_id}", response_model=Dict[str, Any])
async def update_document_category(
    category_id: int = Path(...),
    category_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    category_service: DocumentCategoryService = Depends(get_document_category_service)
):
    """
    Cập nhật thông tin danh mục tài liệu.
    """
    category = await category_service.update_category(category_id, category_data)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Danh mục tài liệu không tồn tại hoặc không thể cập nhật"
        )
    
    return category.__dict__


@router.delete("/document-categories/{category_id}", response_model=Dict[str, Any])
async def delete_document_category(
    category_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    category_service: DocumentCategoryService = Depends(get_document_category_service)
):
    """
    Xóa danh mục tài liệu.
    """
    success = await category_service.delete_category(category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Danh mục tài liệu không tồn tại hoặc không thể xóa"
        )
    
    return {"success": True, "message": "Danh mục tài liệu đã được xóa thành công"}
