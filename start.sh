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

chmod +x ./gateway/src/*.py
chmod +x ./service-word/src/*.py
chmod +x ./service-excel/src/*.py
chmod +x ./service-pdf/src/*.py

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
echo "- RabbitMQ Management: http://localhost:15672"
echo "  Username: admin"
echo "  Password: adminpassword"
echo "- MinIO Console: http://localhost:9001"
echo "  Username: minioadmin"
echo "  Password: minioadmin"
echo ""
echo "Để dừng hệ thống, sử dụng lệnh: ./stop.sh"