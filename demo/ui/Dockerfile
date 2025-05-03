FROM python:3.13-slim
WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency definition files and README
COPY demo/ui/pyproject.toml demo/ui/uv.lock* demo/ui/README.md ./

# Install all deps into the system interpreter at build‑time
RUN uv pip install --system --no-cache-dir -r pyproject.toml

# Copy the rest of the UI code to its proper subdirectory
COPY demo/ui/ /app/ui/

# Copy common library for imports
COPY common/ /app/common/

# Add app directory to Python path
ENV PYTHONPATH="/app:${PYTHONPATH}"

EXPOSE 12000
ENV ORCHESTRATOR_URL="http://orchestrator:8000"

# Run Python directly instead of using uv run
CMD ["python", "/app/ui/main.py", "--host", "0.0.0.0", "--port", "12000"]
