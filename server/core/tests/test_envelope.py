import pytest
from rest_framework import status
from rest_framework.test import APIClient

@pytest.fixture
def api_client():
    return APIClient()

def test_unknown_api_url_returns_json_error_envelope_404(api_client):
    response = api_client.get("/api/unknown-endpoint-404/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "The requested resource was not found.",
            "details": {},
        }
    }

@pytest.mark.django_db
def test_validation_error_returns_json_error_envelope_400(api_client):
    response = api_client.post("/api/auth/login/", {}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "username" in data["error"]["details"]
    assert "password" in data["error"]["details"]
