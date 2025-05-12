    document-processing-system/
    ├── docker-compose.yml                # Cấu hình Docker Compose
    ├── .env                              # Biến môi trường
    ├── .env.example                      # Mẫu biến môi trường
    ├── README.md                         # Tài liệu chính
    ├── start.sh                          # Script khởi động hệ thống
    ├── stop.sh                           # Script dừng hệ thống
    │
    ├── gateway/                          # Gateway API
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── src/
    │       ├── __init__.py
    │       ├── main.py                   # Điểm vào ứng dụng
    │       ├── core/                     # Module lõi
    │       │   ├── __init__.py
    │       │   ├── config.py             # Cấu hình
    │       │   ├── middlewares.py        # Middleware
    │       │   └── security.py           # Xác thực & bảo mật
    │       ├── api/                      # API routes
    │       │   ├── __init__.py
    │       │   ├── v1/                   # API phiên bản 1
    │       │   │   ├── __init__.py
    │       │   │   ├── endpoints/        # Các endpoint
    │       │   │   │   ├── __init__.py
    │       │   │   │   ├── word_docs.py  # API cho tài liệu Word
    │       │   │   │   ├── excel_docs.py # API cho tài liệu Excel
    │       │   │   │   └── pdf_docs.py   # API cho tài liệu PDF
    │       │   │   └── router.py         # Router API v1
    │       │   └── health.py             # Health check
    │       └── utils/                    # Tiện ích
    │           ├── __init__.py
    │           └── client.py             # HTTP client
    │
    ├── service-word/                     # Dịch vụ Word
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── src/
    │   │   ├── __init__.py
    │   │   ├── main.py                   # Điểm vào ứng dụng
    │   │   ├── core/                     # Module lõi
    │   │   │   ├── __init__.py
    │   │   │   └── config.py             # Cấu hình
    │   │   ├── api/                      # API routes
    │   │   │   ├── __init__.py
    │   │   │   └── routes.py             # Định nghĩa các routes
    │   │   ├── domain/                   # Lớp domain
    │   │   │   ├── __init__.py
    │   │   │   ├── models.py             # Domain models
    │   │   │   └── exceptions.py         # Domain exceptions
    │   │   ├── application/              # Lớp application
    │   │   │   ├── __init__.py
    │   │   │   ├── dto.py                # Data Transfer Objects
    │   │   │   └── services.py           # Service/Use cases
    │   │   ├── infrastructure/           # Lớp infrastructure
    │   │   │   ├── __init__.py
    │   │   │   ├── repository.py         # Repository
    │   │   │   ├── minio_client.py       # MinIO client
    │   │   │   └── rabbitmq_client.py    # RabbitMQ client
    │   │   └── utils/                    # Tiện ích
    │   │       ├── __init__.py
    │   │       └── docx_utils.py         # Tiện ích xử lý Word
    │   ├── tests/                        # Unit tests
    │   │   ├── __init__.py
    │   │   ├── test_services.py
    │   │   └── test_routes.py
    │   ├── templates/                    # Thư mục mẫu Word
    │   └── temp/                         # Thư mục tạm
    │
    ├── service-excel/                    # Dịch vụ Excel
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── src/
    │   │   ├── __init__.py
    │   │   ├── main.py                   # Điểm vào ứng dụng
    │   │   ├── core/                     # Module lõi
    │   │   │   ├── __init__.py
    │   │   │   └── config.py             # Cấu hình
    │   │   ├── api/                      # API routes
    │   │   │   ├── __init__.py
    │   │   │   └── routes.py             # Định nghĩa các routes
    │   │   ├── domain/                   # Lớp domain
    │   │   │   ├── __init__.py
    │   │   │   ├── models.py             # Domain models
    │   │   │   └── exceptions.py         # Domain exceptions
    │   │   ├── application/              # Lớp application
    │   │   │   ├── __init__.py
    │   │   │   ├── dto.py                # Data Transfer Objects
    │   │   │   └── services.py           # Service/Use cases
    │   │   ├── infrastructure/           # Lớp infrastructure
    │   │   │   ├── __init__.py
    │   │   │   ├── repository.py         # Repository
    │   │   │   ├── minio_client.py       # MinIO client
    │   │   │   └── rabbitmq_client.py    # RabbitMQ client
    │   │   └── utils/                    # Tiện ích
    │   │       ├── __init__.py
    │   │       └── excel_utils.py        # Tiện ích xử lý Excel
    │   ├── tests/                        # Unit tests
    │   │   ├── __init__.py
    │   │   ├── test_services.py
    │   │   └── test_routes.py
    │   ├── templates/                    # Thư mục mẫu Excel
    │   └── temp/                         # Thư mục tạm
    │
    ├── service-pdf/                      # Dịch vụ PDF
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── src/
    │   │   ├── __init__.py
    │   │   ├── main.py                   # Điểm vào ứng dụng
    │   │   ├── core/                     # Module lõi
    │   │   │   ├── __init__.py
    │   │   │   └── config.py             # Cấu hình
    │   │   ├── api/                      # API routes
    │   │   │   ├── __init__.py
    │   │   │   └── routes.py             # Định nghĩa các routes
    │   │   ├── domain/                   # Lớp domain
    │   │   │   ├── __init__.py
    │   │   │   ├── models.py             # Domain models
    │   │   │   └── exceptions.py         # Domain exceptions
    │   │   ├── application/              # Lớp application
    │   │   │   ├── __init__.py
    │   │   │   ├── dto.py                # Data Transfer Objects
    │   │   │   └── services.py           # Service/Use cases
    │   │   ├── infrastructure/           # Lớp infrastructure
    │   │   │   ├── __init__.py
    │   │   │   ├── repository.py         # Repository
    │   │   │   ├── minio_client.py       # MinIO client
    │   │   │   └── rabbitmq_client.py    # RabbitMQ client
    │   │   └── utils/                    # Tiện ích
    │   │       ├── __init__.py
    │   │       ├── pdf_utils.py          # Tiện ích xử lý PDF
    │   │       └── image_utils.py        # Tiện ích xử lý hình ảnh
    │   ├── tests/                        # Unit tests
    │   │   ├── __init__.py
    │   │   ├── test_services.py
    │   │   └── test_routes.py
    │   ├── templates/                    # Thư mục mẫu dấu (stamp)
    │   └── temp/                         # Thư mục tạm
    │
    ├── rabbitmq/                         # Cấu hình RabbitMQ
    │   ├── Dockerfile
    │   └── rabbitmq.conf                 # Cấu hình RabbitMQ
    │
    ├── minio/                            # Cấu hình MinIO
    │   ├── Dockerfile
    │   └── config/                       # Cấu hình MinIO
    │       └── config.json
    │
    └── data/                             # Thư mục lưu trữ dữ liệu
        ├── minio/                        # Dữ liệu MinIO
        └── rabbitmq/                     # Dữ liệu RabbitMQ