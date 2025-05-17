FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir minio

COPY init-minio-buckets.py .

CMD ["python", "init-minio-buckets.py"]