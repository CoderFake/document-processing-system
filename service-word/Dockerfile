FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./

RUN mkdir -p /app/temp /app/templates

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6001"]

EXPOSE 6001