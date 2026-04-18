FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi==0.115.12 \
    uvicorn[standard]==0.34.0 \
    httpx==0.28.1 \
    pydantic==2.10.6


# Copy application code
COPY simulator.py .
COPY llm_service.py .
COPY main.py .

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
