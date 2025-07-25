# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the code
COPY src/ ./src/

# Expose the port your server runs on (adjust if needed)
EXPOSE 8000

# Set environment variables (override in Azure)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Start the server
CMD ["python3", "src/server.py"]