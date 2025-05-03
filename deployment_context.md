# Deployment Context: Multi-Agent System on DigitalOcean

## 1. Goal

Deploy the A2A multi-agent system (Orchestrator, Financial, Sentiment, Visualization, UI) with a shared PostgreSQL database to a DigitalOcean droplet using Docker and Docker Compose for containerization and orchestration.

## 2. Components

*   **Orchestrator Agent (`orchestrator_agent`):** Google ADK based, central controller.
*   **Financial Agent (`financial_agent_langgraph`):** LangGraph based, uses OpenAI, connects to Postgres and external MCP server (`mcp-crypto-price`). Requires Node.js/npx.
*   **Sentiment Analysis Agent (`sentiment_analysis_agent`):** CrewAI based, uses Google API, connects to Reddit MCP server (assumed).
*   **Visualization Agent (`visualization_agent`):** CrewAI based, uses Google API, generates plots with Matplotlib, uses in-memory cache.
*   **User Interface (`demo/ui`):** Python-based UI (uses `uv`), interacts with Orchestrator.
*   **Database:** PostgreSQL (running in Docker).
*   **Scraper Scripts (`scraper_agent`):** Standalone Python scripts to populate the Postgres DB using CoinMarketCap API. Not a full agent.

## 3. Technology Stack

*   **Containerization:** Docker
*   **Orchestration:** Docker Compose
*   **Target Environment:** DigitalOcean Droplet (Ubuntu 22.04 LTS recommended)
*   **Language:** Python 3.10
*   **Database:** PostgreSQL 15
*   **UI Runner:** `uv`
*   **Financial Agent Dependency:** Node.js/npm (for `npx`)

## 4. Configuration Summary

*   **Internal Container Ports:**
    *   Orchestrator: `8000`
    *   Financial Agent: `8001`
    *   Sentiment Agent: `10000`
    *   Visualization Agent: `8004`
    *   UI: `12000`
    *   Postgres: `5432`
*   **External Port Mapping:** Host Port `80` -> UI Container Port `12000`.
*   **Secrets Management:** Use a `.env` file in the project root on the droplet for API keys (OpenAI, Google, CoinCap, CMC) and the database password. Restrict permissions (`chmod 600 .env`).
*   **Database Initialization:** An `init_db.sql` file containing `CREATE TABLE` statements should be placed in the project root and will be mounted into the Postgres container to run on first startup.
*   **Agent Execution:** Agents are run using `python -m <module_name>` or specific startup scripts (e.g., `start_agent_server.py`) as defined in their respective Dockerfile `CMD`.
*   **UI Execution:** The UI is run via `uv run main.py --host 0.0.0.0 --port 12000` inside its container.
*   **Inter-service Communication:** Services communicate using their service names and internal ports over the Docker bridge network (`app-net`) defined in `docker-compose.yml`.

## 5. Dockerfiles

### 5.1 `orchestrator_agent/Dockerfile`

```dockerfile
# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY orchestrator_agent/requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir reduces image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent's code and the common library
# Assumes 'common' is one level up relative to the Dockerfile context
COPY orchestrator_agent/ .
COPY common/ common/

# Make port 8000 available inside the container network
EXPOSE 8000

# Define environment variables (can be overridden by docker-compose)
ENV PORT=8000
ENV HOST=0.0.0.0
# Add other ENV vars needed by the orchestrator (Agent URLs, API Keys - set in compose)

# Run the agent as a module when the container launches
CMD ["python", "-m", "orchestrator_agent"]
```

### 5.2 `financial_agent_langgraph/Dockerfile`

```dockerfile
# Use a base image with Python
FROM python:3.10-slim

# Install Node.js and npm (needed for npx mcp-crypto-price)
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && \\
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
```

### 5.3 `sentiment_analysis_agent/Dockerfile`

```dockerfile
FROM python:3.10-slim
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
```

### 5.4 `visualization_agent/Dockerfile`

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY visualization_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY visualization_agent/ .
COPY common/ common/

# Make port 8004 available inside the container network
EXPOSE 8004

# Define environment variables (can be overridden by docker-compose)
ENV PORT=8004
ENV HOST=0.0.0.0
# Add other ENV vars (GOOGLE_API_KEY - set in compose)

# Assuming server.py can be run directly and respects PORT/HOST env vars
# If not, adjust the CMD or the server.py script
CMD ["python", "visualization_agent/server.py"]
```

### 5.5 `demo/ui/Dockerfile`

```dockerfile
FROM python:3.10-slim
WORKDIR /app

# Install uv
RUN pip install uv

# Copy UI code and dependencies definition
COPY demo/ui/pyproject.toml demo/ui/uv.lock* ./
COPY demo/ui/requirements.txt ./ # Assuming uv might use this or pyproject

# Install dependencies using uv
# Adjust if your pyproject.toml requires specific uv commands
RUN uv pip install --no-cache-dir -r requirements.txt

COPY demo/ui/ .

# Make port 12000 available inside the container network
EXPOSE 12000

# Set environment variable for Orchestrator URL (set in compose)
# Orchestrator URL uses its internal port 8000
ENV ORCHESTRATOR_URL="http://orchestrator:8000"

# Run the UI using uv on the correct host and port
CMD ["uv", "run", "main.py", "--host", "0.0.0.0", "--port", "12000"]
```

## 6. Docker Compose (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15 # Use a specific version
    container_name: postgres_db
    environment:
      POSTGRES_DB: ${DB_NAME:-financial_db}
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme} # Use .env file for password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init_db.sql:/docker-entrypoint-initdb.d/init_db.sql # Mount init script
    networks:
      - app-net
    restart: unless-stopped

  orchestrator:
    build:
      context: .
      dockerfile: orchestrator_agent/Dockerfile
    container_name: orchestrator_agent
    environment:
      # API Keys (loaded from .env)
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
      # Agent URLs (using service names and CORRECTED ports)
      FINANCIAL_AGENT_URL: "http://financial:8001" # CORRECTED PORT
      SENTIMENT_AGENT_URL: "http://sentiment:10000"
      VISUALIZATION_AGENT_URL: "http://visualization:8004"
      # Add any other URLs needed (competitor, prompt_templates if implemented)
    networks:
      - app-net
    depends_on:
      - financial
      - sentiment
      - visualization
    restart: unless-stopped
    # No ports exposed by default, only UI needs direct external access typically

  financial:
    build:
      context: .
      dockerfile: financial_agent_langgraph/Dockerfile
    container_name: financial_agent
    environment:
      # API Keys
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      COINCAP_API_KEY: ${COINCAP_API_KEY}
      # Database Connection
      DB_HOST: postgres # Service name of the postgres container
      DB_PORT: 5432
      DB_NAME: ${DB_NAME:-financial_db}
      DB_USER: ${DB_USER:-postgres}
      DB_PASSWORD: ${DB_PASSWORD:-changeme}
      PORT: 8001 # Ensure this matches the Dockerfile's EXPOSE/ENV if used
      HOST: 0.0.0.0
    networks:
      - app-net
    depends_on:
      - postgres
    restart: unless-stopped

  sentiment:
    build:
      context: .
      dockerfile: sentiment_analysis_agent/Dockerfile
    container_name: sentiment_agent
    environment:
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
      SENTIMENT_AGENT_PORT: 10000 # Ensure this matches the Dockerfile's EXPOSE/ENV if used
      HOST: 0.0.0.0
      # Add any other needed env vars (e.g., Reddit API if MCP server requires)
    networks:
      - app-net
    restart: unless-stopped

  visualization:
    build:
      context: .
      dockerfile: visualization_agent/Dockerfile
    container_name: visualization_agent
    environment:
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
      PORT: 8004 # Ensure this matches the Dockerfile's EXPOSE/ENV if used
      HOST: 0.0.0.0
    networks:
      - app-net
    restart: unless-stopped

  ui:
    build:
      context: .
      dockerfile: demo/ui/Dockerfile
    container_name: ui_app
    ports:
      - "80:12000" # Map host port 80 to CORRECTED container port 12000
    environment:
      # UI talks to orchestrator on its internal port 8000
      ORCHESTRATOR_URL: "http://orchestrator:8000"
    networks:
      - app-net
    depends_on:
      - orchestrator # UI needs orchestrator to be ready
    restart: unless-stopped

networks:
  app-net:
    driver: bridge

volumes:
  postgres_data: # Define a named volume for postgres data persistence
```

## 7. Deployment Steps (Summary)

1.  **Prepare Droplet:** Create DigitalOcean Droplet (Ubuntu 22.04 recommended). Install Docker, Docker Compose. Configure UFW (Allow SSH, Port 80).
2.  **Transfer Code:** Clone Git repo or use `scp`/`rsync` to copy the entire project directory (including Dockerfiles, `docker-compose.yml`, `init_db.sql`) to the droplet.
3.  **Create `.env` File:** In the project root on the droplet, create `.env` with necessary API keys and DB password. Set permissions (`chmod 600 .env`).
4.  **Build Images:** In the project root, run `docker compose build`.
5.  **Start Services:** Run `docker compose up -d`.
6.  **Verify Containers:** Run `docker compose ps` to check if all services are running. Check logs (`docker compose logs <service_name>`) for errors, especially `postgres` initially.
7.  **Populate Database:**
    *   Define a `scraper` service in `docker-compose.yml` (see previous plan for example).
    *   Create `scraper_agent/Dockerfile`.
    *   Add `CMC_API_KEY` to `.env`.
    *   Modify scraper scripts to read DB config from ENV and use `DB_HOST=postgres`.
    *   Run scraper(s): `docker compose run --rm scraper python scraper_agent/prices_scraping.py` (and potentially `crypto_history.py`).
8.  **Access UI:** Navigate to `http://YOUR_DROPLET_IP` in a web browser.

## 8. Assumptions

*   Project structure matches the directories used in `docker-compose.yml` build contexts and Dockerfile `COPY` commands.
*   The `common` library directory exists at the project root level alongside agent directories.
*   `MCP-servers/postgres_mcp.py` exists relative to the project root.
*   `init_db.sql` contains the correct SQL `CREATE TABLE` statements for the Postgres DB schema.
*   All necessary API keys (OpenAI, Google, CoinCap, CMC) are available and correctly placed in the `.env` file. 