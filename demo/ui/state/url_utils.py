from urllib.parse import urlparse, urljoin
import os

def normalize_base(url: str | None) -> str:
    url = url or "orchestrator:8000"
    if not urlparse(url).scheme:
        url = f"http://{url}"
    return url.rstrip('/')

BASE = normalize_base(os.getenv("ORCHESTRATOR_URL"))

def api(path: str) -> str:
    return urljoin(BASE + "/", path.lstrip('/')) 