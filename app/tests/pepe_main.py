from fastapi.testclient import TestClient
import logging

from main import app

# Create logger
logging.basicConfig(
    format='%(levelname)s - %(asctime)s - %(message)s', level=logging.INFO)
log = logging.getLogger(__name__)

def test_read_main():
    with TestClient(app) as client:
        response = client.get("/api/ping")
        assert response.status_code == 200
        assert response.json() == {"payload": "Hello, v1.0.1", "pepe": "started"}

def test_list_issuers():
    with TestClient(app) as client:
        response = client.get("/api/trusted-issuers-registry/v1/issuers")
        assert response.status_code == 200
        log.info(f"{response.json()}")