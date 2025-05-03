FROM python:3.13-slim
WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency definition files
COPY demo/ui/pyproject.toml demo/ui/uv.lock* ./

# Install exactly what is pinned in uv.lock
RUN uv sync --system --no-cache-dir

# Copy the rest of the UI code
COPY demo/ui/ .

EXPOSE 12000
ENV ORCHESTRATOR_URL="http://orchestrator:8000"

CMD ["uv", "run", "main.py", "--host", "0.0.0.0", "--port", "12000"]
