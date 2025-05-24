FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app:/app/src

RUN pip install --no-cache-dir numpy==1.24.3

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/temp /app/templates

WORKDIR /app/src

EXPOSE 10002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10002"]