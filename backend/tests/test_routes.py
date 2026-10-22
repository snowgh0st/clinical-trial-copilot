"""
backend/tests/test_routes.py

PURPOSE:
Integration tests for FastAPI endpoints using TestClient.

EXECUTION:
    PYTHONPATH=. python -m pytest backend/tests/test_routes.py
"""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_ehr_upload_note():
    payload = {
        "clinical_note": "Patient presents with Type 2 Diabetes taking Metformin."
    }
    response = client.post("/api/v1/ehr/upload", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "parsed_patient" in data
    assert "extracted_entities" in data