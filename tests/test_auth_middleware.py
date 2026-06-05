from fastapi.testclient import TestClient
import main


def test_mcp_requires_bearer():
    c = TestClient(main.app)
    r = c.get("/mcp")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers
    assert "resource_metadata" in r.headers["WWW-Authenticate"]
