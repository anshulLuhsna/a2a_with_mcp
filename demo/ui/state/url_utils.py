from urllib.parse import urlparse, urljoin
import os

def normalize_base(url: str | None) -> str:
    """Normalize the base URL to ensure it has a scheme and no trailing slashes."""
    # Use the provided URL or default to the localhost UI server URL
    url = url or f"http://localhost:{os.environ.get('A2A_UI_PORT', '12000')}" 
    parsed = urlparse(url)
    # Check if the scheme is specifically http or https
    if parsed.scheme not in ('http', 'https'): 
        # Scheme is missing or is not http/https (like 'orchestrator')
        url = f"http://{url.rstrip('/')}"
    
    final_url = url.rstrip('/')
    print(f"[url_utils] Normalized base URL: {repr(final_url)}")
    return final_url

# Calculate BASE at module level using the environment variable for the LOCAL UI server
# This is what ConversationServer expects host_agent_service to talk to.
BASE = normalize_base(os.getenv("A2A_UI_SELF_URL")) # Use a specific var or construct from host/port
print(f"[url_utils] Using BASE URL for host_agent_service: {repr(BASE)}") 

def api(path: str) -> str:
    """Convert a relative API path to a full URL relative to the BASE."""
    # Ensure base_url ends with a slash for urljoin
    base_url_with_slash = BASE if BASE.endswith('/') else BASE + '/'
    
    # Do NOT prepend /mcp/ here, as ConversationServer defines routes at the root
    url = urljoin(base_url_with_slash, path.lstrip('/')) 
    print(f"[url_utils] Constructed API URL for host_agent_service: {repr(url)}")
    return url 