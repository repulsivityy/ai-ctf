FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (curl required for healthcheck)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose the API port
EXPOSE 8000

# Healthcheck (see docs/DEPLOYMENT_OPS.md)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/healthz || exit 1

# Single worker — chat history is held in-process (see server.py).
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
