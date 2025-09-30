FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/

# Expose port
EXPOSE 8000

# Run database initialization and start server
CMD python scripts/init_db.py && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
