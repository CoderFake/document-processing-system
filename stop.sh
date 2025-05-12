#!/bin/bash

echo "=== Dừng hệ thống xử lý tài liệu ==="

docker-compose down

echo "Đã dừng tất cả các dịch vụ."
echo "Để khởi động lại hệ thống, sử dụng lệnh: ./start.sh"