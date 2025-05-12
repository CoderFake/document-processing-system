    document-processing-system/
    ├── docker-compose.yml                # Cấu hình Docker Compose
    ├── .env                              # Biến môi trường
    ├── .env.example                      # Mẫu biến môi trường
    ├── README.md                         # Tài liệu chính
    ├── start.sh                          # Script khởi động hệ thống
    ├── stop.sh                           # Script dừng hệ thống
    ├── init-db.sh                        # Script khởi tạo cơ sở dữ liệu
    ├── remove_comments.py                # Tiện ích xử lý mã nguồn
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
    │       │   │   │   ├── pdf_docs.py   # API cho tài liệu PDF
    │       │   │   │   ├── files.py      # API cho tệp tin nén
    │       │   │   │   └── users.py      # API cho người dùng
    │       │   │   └── router.py         # Router API v1
    │       │   └── health.py             # Health check
    │       └── utils/                    # Tiện ích
    │           ├── __init__.py
    │           └── client.py             # HTTP client
    │
    ├── service-user/                     # Dịch vụ quản lý người dùng
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── src/
    │       ├── __init__.py
    │       ├── main.py                   # Điểm vào ứng dụng
    │       ├── core/                     # Module lõi
    │       │   ├── __init__.py
    │       │   ├── config.py             # Cấu hình
    │       │   └── security.py           # Xác thực & mã hóa
    │       ├── api/                      # API routes
    │       │   ├── __init__.py
    │       │   ├── deps.py               # Các dependencies
    │       │   └── routes.py             # Định nghĩa các routes
    │       ├── domain/                   # Lớp domain
    │       │   ├── __init__.py
    │       │   ├── models.py             # Domain models (User, Role, Permission)
    │       │   └── exceptions.py         # Domain exceptions
    │       ├── application/              # Lớp application
    │       │   ├── __init__.py
    │       │   ├── dto.py                # Data Transfer Objects
    │       │   └── services.py           # Service/Use cases
    │       └── infrastructure/           # Lớp infrastructure
    │           ├── __init__.py
    │           ├── repository.py         # Repository
    │           └── database.py           # Kết nối database
    │
    ├── service-word/                     # Dịch vụ xử lý Word
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── src/
    │   │   ├── __init__.py
    │   │   ├── main.py                   # Điểm vào ứng dụng
    │   │   ├── word.proto                # gRPC protocol
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
    │   │       ├── grpc_server.py        # gRPC server
    │   │       ├── word_pb2.py           # gRPC generated code
    │   │       ├── word_pb2_grpc.py      # gRPC generated code
    │   │       ├── word_service.py       # Triển khai WordService
    │   │       └── docx_utils.py         # Tiện ích xử lý Word
    │   ├── tests/                        # Unit tests
    │   │   ├── __init__.py
    │   │   ├── test_services.py
    │   │   └── test_routes.py
    │   ├── templates/                    # Thư mục mẫu Word
    │   └── temp/                         # Thư mục tạm
    │
    ├── service-files/                    # Dịch vụ xử lý tệp nén
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
    │   │   └── infrastructure/           # Lớp infrastructure
    │   │       ├── __init__.py
    │   │       ├── repository.py         # Repository
    │   │       ├── minio_client.py       # MinIO client
    │   │       └── rabbitmq_client.py    # RabbitMQ client
    │   ├── tests/                        # Unit tests
    │   │   ├── __init__.py
    │   │   ├── test_services.py
    │   │   └── test_routes.py
    │   ├── templates/                    # Thư mục mẫu
    │   └── temp/                         # Thư mục tạm
    │
    ├── service-excel/                    # Dịch vụ xử lý Excel
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
    ├── service-pdf/                      # Dịch vụ xử lý PDF
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
        ├── postgres/                     # Dữ liệu PostgreSQL
        └── rabbitmq/                     # Dữ liệu RabbitMQ