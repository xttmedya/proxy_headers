FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .  
COPY app.py .

RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 7860

CMD ["gunicorn", "app:app", \
     "-w", "4", \
     "--worker-class", "gthread", \
     "--threads", "4", \
     "--bind", "0.0.0.0:7860", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100"]
