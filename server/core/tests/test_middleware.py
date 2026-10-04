from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import APIClient

from core.middleware import NoStoreCacheMiddleware


def test_api_responses_have_no_store_header():
    client = APIClient()
    response = client.get("/api/health/")
    assert response.headers.get("Cache-Control") == "no-store"


def test_non_api_paths_do_not_have_no_store():
    factory = RequestFactory()
    request = factory.get("/non-api/test/")
    middleware = NoStoreCacheMiddleware(lambda req: HttpResponse("ok"))
    response = middleware(request)
    assert response.headers.get("Cache-Control") != "no-store"
