#!/bin/bash

echo "=== Khởi động hệ thống xử lý tài liệu ==="
echo "Sử dụng docker-compose..."

mkdir -p ./data/minio
mkdir -p ./data/rabbitmq

mkdir -p ./gateway/src/temp
mkdir -p ./service-word/src/temp
mkdir -p ./service-word/src/templates
mkdir -p ./service-excel/src/temp
mkdir -p ./service-excel/src/templates
mkdir -p ./service-pdf/src/temp
mkdir -p ./service-pdf/src/templates
mkdir -p ./service-files/src/temp
mkdir -p ./service-files/src/templates
mkdir -p ./service-user/src/temp
mkdir -p ./service-user/src/templates

chmod +x ./gateway/src/*.py
chmod +x ./service-word/src/*.py
chmod +x ./service-excel/src/*.py
chmod +x ./service-pdf/src/*.py
chmod +x ./service-files/src/*.py
chmod +x ./service-user/src/*.py
chmod +x ./init-db.sh

if ! command -v docker &> /dev/null; then
    echo "Docker chưa được cài đặt. Vui lòng cài đặt Docker trước."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose chưa được cài đặt. Vui lòng cài đặt Docker Compose trước."
    exit 1
fi

echo "Khởi động dịch vụ..."
docker-compose up -d

echo "Đang chờ các dịch vụ khởi động..."
sleep 10

echo "Kiểm tra trạng thái dịch vụ..."
docker-compose ps

echo ""
echo "=== Hệ thống xử lý tài liệu đã khởi động ==="
echo "- Gateway API: http://localhost:6000/docs"
echo "- Word Service: http://localhost:6001/docs"
echo "- Excel Service: http://localhost:6002/docs"
echo "- PDF Service: http://localhost:6003/docs"
echo "- Files Service: http://localhost:6004/docs"
echo "- User Service: http://localhost:6005/docs"
echo "- PostgreSQL: http://localhost:6006"
echo "- RabbitMQ Management: http://localhost:15672"
echo "- MinIO Console: http://localhost:9001"
echo "  Username: admin"
echo "  Admin Email: admin@admin.com"
echo "  Password: password123"
echo "  MinIO Username: minioadmin"
echo "  MinIO Password: minioadmin"
echo ""
echo "Để dừng hệ thống, sử dụng lệnh: ./stop.sh"