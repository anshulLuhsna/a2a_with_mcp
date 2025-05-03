# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy common library FIRST
COPY common/ /app/common/

# Copy requirements and install
COPY orchestrator_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code AFTER installing requirements to the proper subdirectory
COPY orchestrator_agent/ /app/orchestrator_agent/

# Install the agent package in development mode to make it importable via -m
RUN pip install -e /app/orchestrator_agent

# Add app directory to Python path
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Make port 8000 available to the world outside this container (mapped in docker-compose)
EXPOSE 8000

# Define environment variables (will be overridden by docker-compose)
ENV PORT=8000
ENV HOST=0.0.0.0
# Add other ENV vars needed by the orchestrator (Agent URLs, API Keys - set in compose)

# Run the agent as a module when the container launches
CMD ["python", "-m", "orchestrator_agent"]