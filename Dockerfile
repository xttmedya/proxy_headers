FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/xttmedya/proxy_headers .

# requirements.txt zaten repo içinde olduğundan tekrar kopyalamana gerek yok
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt || \
    pip install flask curl-cffi m3u8 gunicorn

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
