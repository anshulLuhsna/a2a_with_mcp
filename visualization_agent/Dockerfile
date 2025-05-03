FROM python:3.12-slim
WORKDIR /app

# Copy common library FIRST
COPY common/ /app/common/

# Copy requirements and install
COPY visualization_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code AFTER installing requirements to the proper subdirectory
COPY visualization_agent/ /app/visualization_agent/

# Add app directory to Python path
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Make port 8004 available inside the container network
EXPOSE 8004

# Define environment variables (can be overridden by docker-compose)
ENV PORT=8004
ENV HOST=0.0.0.0
# Add other ENV vars (GOOGLE_API_KEY - set in compose)

# Use the full path to the server.py file
CMD ["python", "/app/visualization_agent/server.py"]
