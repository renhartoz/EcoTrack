from django.http import Http404, JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is None:
        if isinstance(exc, Http404):
            response = Response(status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, exceptions.PermissionDenied):
            response = Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return None

    status_code = response.status_code
    error_code = "UNKNOWN_ERROR"
    message = "An error occurred."
    details = {}

    if status_code == status.HTTP_401_UNAUTHORIZED:
        error_code = "UNAUTHENTICATED"
        message = "Authentication credentials were not provided or are invalid."
    elif status_code == status.HTTP_403_FORBIDDEN:
        exc_str = str(exc).lower()
        if "csrf" in exc_str:
            error_code = "CSRF_FAILED"
            message = "CSRF check failed."
        else:
            error_code = "FORBIDDEN"
            message = "You do not have permission to perform this action."
    elif status_code == status.HTTP_404_NOT_FOUND:
        error_code = "NOT_FOUND"
        message = "The requested resource was not found."
    elif status_code == status.HTTP_400_BAD_REQUEST:
        error_code = "VALIDATION_ERROR"
        message = "Request validation failed."
    elif status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        error_code = "THROTTLED"
        message = "Request was throttled. Expected available in seconds."
    elif status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
        error_code = "FILE_TOO_LARGE"
        message = "File exceeds the allowed upload size."
    elif status_code == 422:
        error_code = "ROW_HAS_HARD_FLAGS"
        message = "Row has hard validation flags."
    elif status_code == status.HTTP_409_CONFLICT:
        error_code = "ROW_NOT_PENDING"
        message = "Row is not in pending status."

    if isinstance(response.data, dict):
        if "detail" in response.data:
            message = str(response.data["detail"])
            custom_code = getattr(response.data["detail"], "code", None)
            if custom_code == "csrf_failed":
                error_code = "CSRF_FAILED"
        else:
            details = response.data
    elif isinstance(response.data, list):
        details = {"non_field_errors": response.data}

    response.data = {
        "error": {
          "code": error_code,
          "message": message,
          "details": details,
        }
    }
    return response

def handler404(request, exception=None):
    return JsonResponse(
        {
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource was not found.",
                "details": {},
            }
        },
        status=404,
    )

def handler500(request):
    return JsonResponse(
        {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal server error occurred.",
                "details": {},
            }
        },
        status=500,
    )
