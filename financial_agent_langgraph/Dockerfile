# Use a base image with Python
FROM python:3.12-slim

# Install Node.js and npm (needed for npx mcp-crypto-price)
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY financial_agent_langgraph/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent code, common library, and the MCP server script
COPY financial_agent_langgraph/ .
COPY common/ common/
# Ensure MCP-servers/postgres_mcp.py exists and is copied relative to build context
COPY MCP-servers/postgres_mcp.py MCP-servers/postgres_mcp.py

# Make port 8001 available inside the container network
EXPOSE 8001

# Define environment variables (can be overridden by docker-compose)
ENV PORT=8001
ENV HOST=0.0.0.0
# Add other ENV vars (DB creds, API Keys - set in compose)

# Run the agent as a module
CMD ["python", "-m", "financial_agent_langgraph"]
