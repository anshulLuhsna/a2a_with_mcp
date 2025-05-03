FROM python:3.12-slim
WORKDIR /app
COPY sentiment_analysis_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY sentiment_analysis_agent/ .
COPY common/ common/

# Make port 10000 available inside the container network
EXPOSE 10000

# Define environment variables (can be overridden by docker-compose)
ENV SENTIMENT_AGENT_PORT=10000
ENV HOST=0.0.0.0
# Add other ENV vars (GOOGLE_API_KEY - set in compose)

# Run the startup script which reads SENTIMENT_AGENT_PORT
CMD ["python", "sentiment_analysis_agent/start_agent_server.py"]
