FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libgl1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    build-essential \
    libpoppler-dev \
    libreoffice \
    poppler-utils \
    fonts-liberation \
    fonts-dejavu \
    fonts-freefont-ttf \
    fontconfig && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/share/fonts/truetype/msttcorefonts

RUN apt-get update && \
    apt-get install -y wget && \
    wget https://ftp.gnome.org/mirror/ubuntu/pool/multiverse/m/msttcorefonts/ttf-mscorefonts-installer_3.8ubuntu1_all.deb && \
    apt-get install -y ./ttf-mscorefonts-installer_3.8ubuntu1_all.deb || true && \
    rm -f ./ttf-mscorefonts-installer_3.8ubuntu1_all.deb && \
    fc-cache -f -v && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app:/app/src

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/temp /app/templates

WORKDIR /app/src

EXPOSE 10003

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10003"] 