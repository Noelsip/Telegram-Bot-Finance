FROM python:3.12-slim

# Install dependency build (untuk numpy, spacy, dll)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

COPY . .

CMD ["python", "bot.py"]