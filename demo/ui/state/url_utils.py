from urllib.parse import urlparse, urljoin
import os

def normalize_base(url: str | None) -> str:
    """Normalize the base URL to ensure it has a scheme and no trailing slashes."""
    # Default if URL is None or empty
    if not url:
        url = "http://orchestrator:8000"
        
    parsed = urlparse(url)
    
    # Add http:// scheme if it's missing from the original URL string
    if not parsed.scheme:
        url = f"http://{url}" # Prepend to the original string
    
    # Ensure no trailing slash
    normalized_url = url.rstrip('/')
    print(f"Corrected Normalized base URL: {normalized_url}") # Updated Debug log
    return normalized_url

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