# Hệ thống xử lý tài liệu - Microservices

Hệ thống xử lý tài liệu đa dạng với kiến trúc microservices, hỗ trợ xử lý các định dạng Word, Excel, PDF và hình ảnh.

## Tổng quan về hệ thống

Hệ thống bao gồm các thành phần sau:

- **Gateway API (6000)**: Cổng giao tiếp chính với người dùng, điều phối yêu cầu đến các dịch vụ.
- **Word Service (6001)**: Xử lý tài liệu Word/DOCX, cung cấp gRPC API để chuyển đổi định dạng.
- **Excel Service (6002)**: Xử lý tài liệu Excel/XLSX, hỗ trợ phân tích và chuyển đổi dữ liệu.
- **PDF Service (6003)**: Xử lý tài liệu PDF và hình ảnh PNG, JPG.
- **Files Service (6004)**: Xử lý nén/giải nén và quản lý các tệp tin đa dạng.
- **User Service (6005)**: Quản lý người dùng, xác thực và phân quyền.
- **PostgreSQL (6006)**: Cơ sở dữ liệu quan hệ để lưu trữ dữ liệu người dùng và metadata.
- **RabbitMQ**: Hệ thống hàng đợi tin nhắn để xử lý công việc bất đồng bộ.
- **MinIO**: Lưu trữ đối tượng tương thích S3 để lưu trữ tài liệu.

## Tính năng chính

### Word Service
- Tải lên và quản lý tài liệu Word
- Chuyển đổi Word sang PDF qua gRPC
- Thêm watermark vào tài liệu Word
- Áp dụng mẫu với dữ liệu (mail merge)
- Tạo hàng loạt tài liệu từ mẫu và tập dữ liệu
- Hỗ trợ mẫu báo cáo thực tập, hợp đồng lao động, giấy khen thưởng và giấy mời

### Excel Service
- Tải lên và quản lý tài liệu Excel
- Chuyển đổi Excel sang PDF/Word
- Gộp nhiều file Excel thành một
- Sử dụng mẫu Excel với dữ liệu động
- Phân tích dữ liệu từ file Excel

### PDF Service
- Tải lên và quản lý tài liệu PDF
- Mã hóa/Giải mã PDF với mật khẩu
- Thêm watermark và chữ ký vào PDF
- Gộp nhiều file PDF
- Chuyển đổi PDF sang hình ảnh 
- Chuyển đổi hình ảnh sang PDF

### Files Service
- Nén và giải nén tệp tin (ZIP, RAR, 7z)
- Tải lên và quản lý các tệp tin đa dạng
- Gộp nhiều tệp tin vào một tệp nén
- Quản lý cấu trúc thư mục trong tệp nén

### User Service
- Đăng ký và quản lý người dùng
- Xác thực bằng JWT token
- Quản lý vai trò và phân quyền
- Làm mới token và quản lý phiên đăng nhập

## Yêu cầu hệ thống

- Docker: 20.10.x trở lên
- Docker Compose: 1.29.x trở lên
- 4GB RAM trở lên
- 10GB dung lượng ổ đĩa trống

## Cài đặt và khởi động

1. Clone repository:

```bash
git clone <repository_url>
cd document-processing-system
```

2. Tạo file .env từ .env.example:

```bash
cp .env.example .env
```

3. Chỉnh sửa các biến môi trường trong file .env nếu cần thiết.

4. Khởi động hệ thống:

```bash
chmod +x start.sh
./start.sh
```

5. Dừng hệ thống:

```bash
./stop.sh
```

## Sử dụng API

Sau khi khởi động, có thể truy cập các API bằng Swagger UI:

- Gateway API: http://localhost:6000/docs
- Word Service: http://localhost:6001/docs
- Excel Service: http://localhost:6002/docs
- PDF Service: http://localhost:6003/docs
- Files Service: http://localhost:6004/docs
- User Service: http://localhost:6005/docs

## Quản trị hệ thống

- RabbitMQ Management: http://localhost:15672 (admin/adminpassword)
- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
- PostgreSQL: 127.0.0.1:6006 (postgres/postgres)

## Cấu trúc thư mục

```
document-processing-system/
├── docker-compose.yml         # Cấu hình Docker Compose cho toàn bộ hệ thống
├── .env                       # Biến môi trường
├── .env.example               # Mẫu biến môi trường
├── start.sh                   # Script khởi động hệ thống
├── stop.sh                    # Script dừng hệ thống
├── init-db.sh                 # Script khởi tạo cơ sở dữ liệu
├── gateway/                   # Mã nguồn Gateway API
├── service-word/              # Mã nguồn Word Service
├── service-excel/             # Mã nguồn Excel Service
├── service-pdf/               # Mã nguồn PDF Service
├── service-files/             # Mã nguồn Files Service
├── service-user/              # Mã nguồn User Service
├── rabbitmq/                  # Cấu hình RabbitMQ
├── minio/                     # Cấu hình MinIO 
└── data/                      # Thư mục lưu trữ dữ liệu
```

## Kiến trúc hệ thống

Hệ thống sử dụng kiến trúc microservices với các thành phần giao tiếp qua REST API và RabbitMQ:

1. **Client**: Gửi yêu cầu tới Gateway API
2. **Gateway API**: Xác thực và phân phối yêu cầu tới các service tương ứng
3. **Microservices**: Thực hiện xử lý nghiệp vụ chuyên biệt
4. **RabbitMQ**: Xử lý các tác vụ bất đồng bộ giữa các service
5. **MinIO**: Lưu trữ tài liệu và các tệp tin
6. **PostgreSQL**: Lưu trữ thông tin người dùng và metadata

## Phát triển

### Quy tắc thiết kế

Hệ thống tuân theo các quy tắc thiết kế sau:

1. **Clean Architecture**: Phân chia rõ ràng các lớp domain, application, infrastructure.
2. **Repository Pattern**: Truy cập dữ liệu qua các repository.
3. **DTO Pattern**: Sử dụng DTO để chuyển dữ liệu giữa các lớp.
4. **Dependency Injection**: Sử dụng DI để giảm sự phụ thuộc giữa các module.
5. **CQRS Pattern**: Phân tách rõ lệnh (command) và truy vấn (query) trong service-user.

### Thêm tính năng mới

1. Tạo hoặc cập nhật DTO trong module `application/dto.py`.
2. Thêm logic xử lý vào service tương ứng trong module `application/services.py`.
3. Thêm endpoint vào router trong module `api/routes.py`.
4. Cập nhật tài liệu API qua chú thích docstring.
5. Thêm unit test cho các tính năng mới.

## Giao tiếp giữa services

- **REST API**: Giao tiếp chính giữa Gateway và microservices
- **gRPC**: Sử dụng cho các thao tác chuyển đổi tài liệu trong Word Service
- **RabbitMQ**: Xử lý các tác vụ nặng và bất đồng bộ

## Giấy phép

Dự án này được phân phối dưới Giấy phép MIT. Xem [LICENSE](./LICENSE) để biết thêm chi tiết.