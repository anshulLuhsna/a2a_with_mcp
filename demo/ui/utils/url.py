from urllib.parse import urlparse, urljoin

def normalize_base(url: str) -> str:
    """Normalize a base URL to ensure it has a proper scheme.
    
    Args:
        url (str): The URL to normalize
        
    Returns:
        str: The normalized URL with scheme (http:// if none was provided)
    """
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"http://{url}"
    return url.rstrip('/') 