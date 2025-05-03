FROM python:3.12-slim
WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency definition files
COPY demo/ui/pyproject.toml demo/ui/uv.lock* ./
COPY demo/ui/requirements.txt ./

# Install dependencies using uv
RUN uv pip install --no-cache-dir -r requirements.txt

# Copy the rest of the UI code
COPY demo/ui/ .

# Make port 12000 available inside the container network
EXPOSE 12000

# Set environment variable for Orchestrator URL (set in compose)
# Orchestrator URL uses its internal port 8000
ENV ORCHESTRATOR_URL="http://orchestrator:8000"

# Run the UI using uv on the correct host and port
CMD ["uv", "run", "main.py", "--host", "0.0.0.0", "--port", "12000"]
