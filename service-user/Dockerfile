FROM python:3.10-slim

WORKDIR /app

ENV PYTHONPATH=/app:/app/src

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install PyJWT

COPY . .

RUN mkdir -p /app/logs
RUN mkdir -p /app/data

WORKDIR /app/src

EXPOSE 10005

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10005"]
