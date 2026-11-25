FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV SIMULATOR_ENABLED=true
ENV WEB_PORT=8080
ENV WEB_HOST=0.0.0.0

EXPOSE 8080

CMD ["python3", "main.py", "--simulate", "--web"]
