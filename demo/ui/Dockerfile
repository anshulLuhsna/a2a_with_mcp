FROM python:3.13-slim
WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency definition files and README
COPY demo/ui/pyproject.toml demo/ui/uv.lock* demo/ui/README.md ./

# Install all deps into the system interpreter at build‑time
RUN uv pip install --system --no-cache-dir -r pyproject.toml

# Copy full UI code (including hosts/) and expose on PYTHONPATH
COPY demo/ui/ /app/ui/
ENV PYTHONPATH="/app/ui:/app:${PYTHONPATH}"

# Copy common library for imports
COPY common/ /app/common/

EXPOSE 12000
ENV ORCHESTRATOR_URL="http://orchestrator:8000"

# Run using the module path
CMD ["python", "-m", "ui.main", "--host", "0.0.0.0", "--port", "12000"]
