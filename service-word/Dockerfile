FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs
RUN mkdir -p /app/temp
RUN mkdir -p /app/templates

ENV PYTHONPATH=/app

EXPOSE 6001

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "6001"]