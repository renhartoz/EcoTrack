from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import exceptions
from rest_framework.permissions import SAFE_METHODS
from rest_framework_simplejwt.authentication import JWTAuthentication


class CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return reason


def enforce_csrf(request):
    raw_request = getattr(request, "_request", request)
    dont_enforce = getattr(raw_request, "_dont_enforce_csrf_checks", False)
    if dont_enforce:
        raw_request._dont_enforce_csrf_checks = False

    try:

        def dummy_get_response(req):
            return None

        check = CSRFCheck(dummy_get_response)
        check.process_request(raw_request)
        reason = check.process_view(raw_request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(
                f"CSRF Failed: {reason}",
                code="csrf_failed",
            )
    finally:
        if dont_enforce:
            raw_request._dont_enforce_csrf_checks = dont_enforce


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        if request.method not in SAFE_METHODS:
            enforce_csrf(request)

        return self.get_user(validated_token), validated_token
