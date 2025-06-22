FROM python:3.12-slim

WORKDIR /app

# Sistem gereksinimlerini yükle
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# GitHub reposunu klonla
RUN git clone https://github.com/xttmedya/proxy_headers . 

# Gereksinim dosyası varsa yükle (yoksa app.py'nin bağımlılıklarını doğrudan yükle)
COPY requirements.txt .  # varsa kullanılır
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt || \
    pip install flask curl-cffi m3u8 gunicorn

# Uygulama dosyasını kopyala (repo dışında dosya ekliyorsan)
# COPY app.py .

EXPOSE 7860

CMD ["gunicorn", "proxy:app", \
     "-w", "4", \
     "--worker-class", "gevent", \
     "--worker-connections", "100", \
     "-b", "0.0.0.0:7860", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100"]
