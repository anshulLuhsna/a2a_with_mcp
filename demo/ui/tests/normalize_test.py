from utils.url import normalize_base

def test_normalize():
    assert normalize_base("orchestrator:8000") == "http://orchestrator:8000"
    assert normalize_base("http://foo") == "http://foo"
    assert normalize_base("https://example.com/") == "https://example.com"
    assert normalize_base("localhost:12000") == "http://localhost:12000"
    assert normalize_base("http://orchestrator:8000/") == "http://orchestrator:8000" 