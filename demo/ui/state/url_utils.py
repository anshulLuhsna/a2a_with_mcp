from urllib.parse import urlparse, urljoin
import os

def normalize_base(url: str | None) -> str:
    """Normalize the base URL to ensure it has a scheme and no trailing slashes."""
    print(f"[normalize_base] Received URL: {repr(url)}")
    input_url = url or "orchestrator:8000"
    print(f"[normalize_base] input_url after default: {repr(input_url)}")

    parsed = urlparse(input_url)
    print(f"[normalize_base] parsed scheme: {repr(parsed.scheme)}")

    final_url = ""
    if parsed.scheme:
        print("[normalize_base] Scheme exists path")
        final_url = input_url.rstrip('/')
    else:
        print("[normalize_base] Scheme MISSING path")
        # Explicitly construct the string to prepend
        scheme_prefix = "http://"
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
    """Convert a relative API path to a full URL using the current ORCHESTRATOR_URL."""
    env_var_value = os.getenv("ORCHESTRATOR_URL")
    print(f"[api] os.getenv value: {repr(env_var_value)}")
    base_url = normalize_base(env_var_value)
    print(f"[api] base_url after normalize: {repr(base_url)}")

    if not base_url.endswith('/'):
        base_url += '/'

    url = urljoin(base_url, path.lstrip('/'))
    print(f"[api] Constructed API URL with urljoin: {repr(url)}")
    return url 