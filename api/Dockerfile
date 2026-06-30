FROM python:3.10-slim

WORKDIR /app/api

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The source code will be mounted from the host into /app in docker-compose.
# We copy it here as a fallback for non-compose environments.
COPY . .

# Expose port
EXPOSE 8000

# Run uvicorn with reload for development
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
