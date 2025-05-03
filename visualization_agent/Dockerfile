FROM python:3.12-slim
WORKDIR /app

# Copy common library FIRST
COPY common/ ./common/

# Copy requirements and install
COPY visualization_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code AFTER installing requirements
COPY visualization_agent/ .

# Make port 8004 available inside the container network
EXPOSE 8004

# Define environment variables (can be overridden by docker-compose)
ENV PORT=8004
ENV HOST=0.0.0.0
# Add other ENV vars (GOOGLE_API_KEY - set in compose)

# Assuming server.py can be run directly and respects PORT/HOST env vars
# If not, adjust the CMD or the server.py script
CMD ["python", "visualization_agent/server.py"]
