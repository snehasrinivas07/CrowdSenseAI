FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi==0.115.12 \
    uvicorn[standard]==0.34.0 \
    httpx==0.28.1 \
    pydantic==2.10.6 \
    python-dotenv==1.2.2

# Copy application code from backend folder
COPY backend/simulator.py backend/
COPY backend/llm_service.py backend/
COPY backend/main.py backend/

# Change working directory so local python module imports work cleanly
WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
