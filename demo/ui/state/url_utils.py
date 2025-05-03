from urllib.parse import urlparse, urljoin
import os

def normalize_base(url: str | None) -> str:
    """Normalize the base URL to ensure it has a scheme and no trailing slashes."""
    input_url = url or "orchestrator:8000" # Use default if None/empty, assign to new var

    parsed = urlparse(input_url)

    # Directly construct the final URL based on scheme presence
    if parsed.scheme:
        # Scheme exists, use the input url directly
        final_url = input_url.rstrip('/')
    else:
        # Scheme is missing, prepend http://
        final_url = f"http://{input_url.rstrip('/')}"

    print(f"Final Normalized base URL: {final_url}") # Updated Debug log
    return final_url

# BASE = normalize_base(os.getenv("ORCHESTRATOR_URL")) # Removed module-level calculation
# print(f"Using orchestrator base URL: {BASE}")  # Removed module-level log

def api(path: str) -> str:
    """Convert a relative API path to a full URL using the current ORCHESTRATOR_URL."""
    base_url = normalize_base(os.getenv("ORCHESTRATOR_URL"))

    # Ensure base_url ends with a slash for urljoin
    if not base_url.endswith('/'):
        base_url += '/'

    url = urljoin(base_url, path.lstrip('/'))
    print(f"Constructed API URL: {url}") # Debug log
    return url 