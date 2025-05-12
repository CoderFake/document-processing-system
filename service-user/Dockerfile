FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs
RUN mkdir -p /app/data

ENV PYTHONPATH=/app

EXPOSE 6005

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "6005"]
