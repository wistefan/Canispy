from fastapi.testclient import TestClient
import logging

from .lserver import app

# Create logger
logging.basicConfig(
    format='%(levelname)s - %(asctime)s - %(message)s', level=logging.INFO)
log = logging.getLogger(__name__)

def test_init():
    with TestClient(app) as client:
        response = client.get("/store/initialize")
        assert response.status_code == 200

def test_inserts():
    with TestClient(app) as client:
        for i in range(10):
            response = client.get(f"/store/{i}/{i+2}")
            assert response.status_code == 200
