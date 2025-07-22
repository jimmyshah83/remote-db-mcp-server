# Use an official Python runtime as a parent image
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Set the working directory
WORKDIR /app/src

# Copy requirements and install dependencies
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install uv && uv pip compile pyproject.toml -o requirements.txt && uv pip install --system -r requirements.txt

# Copy the rest of the code
COPY src/ .

# Expose the port your server runs on (adjust if needed)
EXPOSE 8000

# Set environment variables (override in Azure)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Start the server
CMD ["python3", "server.py"]