from urllib.parse import urlparse, urljoin
import os

def normalize_base(url: str | None) -> str:
    """Normalize the base URL to ensure it has a scheme (http/https) and no trailing slashes."""
    print(f"[normalize_base] Received URL: {repr(url)}")
    input_url = url or "orchestrator:8000"
    print(f"[normalize_base] input_url after default: {repr(input_url)}")

    parsed = urlparse(input_url)
    print(f"[normalize_base] parsed scheme: {repr(parsed.scheme)}")

    final_url = ""
    # Check if the scheme is specifically http or https
    if parsed.scheme in ('http', 'https'): 
        print(f"[normalize_base] Scheme '{parsed.scheme}' exists path")
        final_url = input_url.rstrip('/')
    else:
        # Scheme is missing or is not http/https (like 'orchestrator')
        print(f"[normalize_base] Scheme MISSING or invalid ('{parsed.scheme}') path")
        scheme_prefix = "http://"
        # Use the original input_url here, as parsing might have misinterpreted it
        url_part = input_url.rstrip('/') 
        print(f"[normalize_base] scheme_prefix: {repr(scheme_prefix)}")
        print(f"[normalize_base] url_part: {repr(url_part)}")
        final_url = f"{scheme_prefix}{url_part}"
        print(f"[normalize_base] final_url inside else: {repr(final_url)}")

    print(f"[normalize_base] Returning final_url: {repr(final_url)}")
    return final_url

# BASE = normalize_base(os.getenv("ORCHESTRATOR_URL")) # Removed module-level calculation
# print(f"Using orchestrator base URL: {BASE}")  # Removed module-level log

def api(path: str) -> str:
    """Convert a relative MCP API path to a full URL using the current ORCHESTRATOR_URL."""
    env_var_value = os.getenv("ORCHESTRATOR_URL")
    print(f"[api] os.getenv value: {repr(env_var_value)}")
    base_url = normalize_base(env_var_value)
    print(f"[api] base_url after normalize: {repr(base_url)}")

    if not base_url.endswith('/'):
        base_url += '/'

    # Prepend /mcp/ to the path for MCP endpoints
    mcp_path = f"mcp/{path.lstrip('/')}"
    print(f"[api] MCP path to join: {repr(mcp_path)}")

    url = urljoin(base_url, mcp_path)
    print(f"[api] Constructed API URL with urljoin: {repr(url)}")
    return url 