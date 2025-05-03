from urllib.parse import urlparse, urljoin
import os

def normalize_base(url: str | None) -> str:
    """Normalize the base URL to ensure it has a scheme and no trailing slashes."""
    url = url or "orchestrator:8000"
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"http://{url}"
    print(f"Normalized base URL: {url}")  # Debug log
    return url.rstrip('/')

# Get the orchestrator URL from the environment, defaulting to http://orchestrator:8000
BASE = normalize_base(os.getenv("ORCHESTRATOR_URL"))
print(f"Using orchestrator base URL: {BASE}")  # Debug log

def api(path: str) -> str:
    """Convert a relative API path to a full URL."""
    url = urljoin(BASE + "/", path.lstrip('/'))
    return url 