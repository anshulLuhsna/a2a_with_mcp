FROM python:3.12-slim
WORKDIR /app

# Copy common library FIRST
COPY common/ /app/common/

# Copy requirements and install
COPY sentiment_analysis_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code AFTER installing requirements to the proper subdirectory
COPY sentiment_analysis_agent/ /app/sentiment_analysis_agent/

# Add app directory to Python path
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Make port 10000 available inside the container network
EXPOSE 10000

# Define environment variables (can be overridden by docker-compose)
ENV SENTIMENT_AGENT_PORT=10000
ENV HOST=0.0.0.0
# Add other ENV vars (GOOGLE_API_KEY - set in compose)

# Use the full path to the startup script
CMD ["python", "/app/sentiment_analysis_agent/start_agent_server.py"]
