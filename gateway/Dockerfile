FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install python-jose[cryptography]
RUN pip install PyJWT
RUN pip install pydantic-settings

COPY . .

RUN mkdir -p /app/temp

ENV PYTHONPATH=/app/src

EXPOSE 10000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "10000"]