FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    gcc \
    tesseract-ocr \
    tesseract-ocr-ind \
    tesseract-ocr-eng \
    libtesseract-dev \
    libpq-dev \
    curl \
    libgl1 \
    libglib2.0-0 \
    bash \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY requirements.txt package.json package-lock.json* ./
COPY prisma ./prisma/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && (npm ci || npm install) \
    && python -m prisma generate

# Copy application code
COPY . .

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create directories
RUN mkdir -p upload/receipts upload/temp exports asset

# Railway will set PORT dynamically
EXPOSE 8000

# ✅ Use entrypoint - Railway akan inject $PORT saat runtime
ENTRYPOINT ["/entrypoint.sh"]