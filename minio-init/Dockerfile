FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir minio>=7.1.0

COPY init-minio-buckets.py .

CMD ["python", "init-minio-buckets.py"] 