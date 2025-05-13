FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app:/app/src

RUN pip install --no-cache-dir numpy==1.24.3

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs
RUN mkdir -p /app/temp
RUN mkdir -p /app/templates

WORKDIR /app/src

EXPOSE 10001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10001"]