FROM python:3.11-slim

WORKDIR /app/backend

# Install dependencies
# We copy requirements.txt to keep it clean. You also had explicit pip install of python-dotenv, so we add it here just in case.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt python-dotenv==1.2.2

# Copy application code (context is already the backend folder)
COPY simulator.py .
COPY llm_service.py .
COPY main.py .

# Cloud Run sets the PORT environment variable dynamically (defaults to 8080)
# We use sh -c to evaluate $PORT at runtime.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
