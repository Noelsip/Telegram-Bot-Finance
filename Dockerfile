FROM python:3.13-slim

# Install system dependencies + Tesseract
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
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Verify Tesseract installed
RUN tesseract --version

WORKDIR /app

# Copy requirements
COPY requirements.txt ./
COPY package.json package-lock.json* ./
COPY prisma ./prisma/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Install Node.js packages
RUN npm config set registry https://registry.npmmirror.com/ \
    && (npm ci || npm install) \
    && npm config set registry https://registry.npmjs.org/

# Generate Prisma Client
RUN python -m prisma generate
# Copy application code
COPY . .

# Create directories
RUN mkdir -p upload/receipts upload/temp exports

CMD ["python", "bot.py"]