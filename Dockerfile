FROM python:3.13-slim

# Install system dependencies + Tesseract + OpenCV
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
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Verify Tesseract installation
RUN tesseract --version

WORKDIR /app

# Copy dependency files
COPY requirements.txt ./
COPY package.json package-lock.json* ./
COPY prisma ./prisma/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Install Node.js packages
RUN npm ci || npm install

# Generate Prisma Client
RUN python -m prisma generate

# Copy application code
COPY . .

# ✅ Copy dan set permission untuk entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8000

# Create required directories
RUN mkdir -p upload/receipts upload/temp exports asset

# Expose port (Railway akan override dengan dynamic port)
EXPOSE $PORT

# ✅ FIX: Gunakan entrypoint script
ENTRYPOINT ["/entrypoint.sh"]