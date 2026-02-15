FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy migration and application code
COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/
COPY automotive/ automotive/

# Expose port
EXPOSE ${PORT:-8000}

# Run migrations on startup, then boot the API
CMD sh -c "python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
