FROM python:3.13-slim
WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency definition files
COPY demo/ui/pyproject.toml demo/ui/uv.lock* ./

# Install exactly what is pinned in uv.lock
RUN uv pip install --system --no-cache-dir -r pyproject.toml

# Copy the rest of the UI code to its proper subdirectory
COPY demo/ui/ /app/ui/

# Copy common library for imports
COPY common/ /app/common/

# Add app directory to Python path
ENV PYTHONPATH="/app:${PYTHONPATH}"

EXPOSE 12000
ENV ORCHESTRATOR_URL="http://orchestrator:8000"

# Use the correct path to main.py 
CMD ["uv", "run", "/app/ui/main.py", "--host", "0.0.0.0", "--port", "12000"]
