from urllib.parse import urlparse, urljoin
import os

def normalize_base(url: str | None) -> str:
    """Normalize the base URL to ensure it has a scheme and no trailing slashes."""
    # Default to orchestrator:8000 if URL is None or empty
    url = url or "http://orchestrator:8000" 
    parsed = urlparse(url)
    if not parsed.scheme:
        # Add http:// if scheme is missing
        url = f"http://{parsed.netloc}{parsed.path}" 
    
    # Ensure no trailing slash
    normalized_url = url.rstrip('/')
    print(f"Normalized base URL: {normalized_url}") # Debug log
    return normalized_url

# BASE = normalize_base(os.getenv("ORCHESTRATOR_URL")) # Removed module-level calculation
# print(f"Using orchestrator base URL: {BASE}")  # Removed module-level log

def api(path: str) -> str:
    """Convert a relative API path to a full URL using the current ORCHESTRATOR_URL."""
    # Get and normalize the base URL *inside* the function
    base_url = normalize_base(os.getenv("ORCHESTRATOR_URL")) 
    
    # Ensure base_url ends with a slash for urljoin to work correctly
    if not base_url.endswith('/'):
        base_url += '/'
        
    # Join the base URL and the path
    url = urljoin(base_url, path.lstrip('/')) 
    print(f"Constructed API URL: {url}") # Debug log
    return url 