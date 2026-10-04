from django.conf import settings
from django.contrib.auth import authenticate
from django.middleware.csrf import get_token
from rest_framework import exceptions, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.authentication import enforce_csrf
from accounts.models import User
from accounts.serializers import LoginSerializer, UserSummarySerializer
from core.throttling import LoginRateThrottle


def set_auth_cookies(response, access_token, refresh_token):
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.JWT_ACCESS_MINUTES * 60,
        httponly=True,
        samesite=settings.JWT_COOKIE_SAMESITE,
        secure=settings.JWT_COOKIE_SECURE,
        path="/api/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.JWT_REFRESH_DAYS * 86400,
        httponly=True,
        samesite=settings.JWT_COOKIE_SAMESITE,
        secure=settings.JWT_COOKIE_SECURE,
        path="/api/auth/",
    )


def clear_auth_cookies(response):
    response.delete_cookie(
        key="access_token",
        path="/api/",
        samesite=settings.JWT_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key="refresh_token",
        path="/api/auth/",
        samesite=settings.JWT_COOKIE_SAMESITE,
    )


def set_csrf_cookie(request, response):
    csrf_token = get_token(request)
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=settings.CSRF_COOKIE_HTTPONLY,
        samesite=settings.CSRF_COOKIE_SAMESITE,
        secure=settings.CSRF_COOKIE_SECURE,
        path="/",
    )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(username=username, password=password)
        if not user or not user.is_active:
            raise exceptions.AuthenticationFailed(
                "Invalid username or password.",
                code="unauthenticated",
            )

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        response = Response(
            {"user": UserSummarySerializer(user).data},
            status=status.HTTP_200_OK,
        )
        set_auth_cookies(response, access, str(refresh))
        set_csrf_cookie(request, response)
        return response


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        enforce_csrf(request)

        refresh_raw = request.COOKIES.get("refresh_token")
        if not refresh_raw:
            raise exceptions.AuthenticationFailed(
                "Refresh token not found in cookies.",
                code="unauthenticated",
            )

        try:
            refresh = RefreshToken(refresh_raw)
            user_id = refresh.payload["user_id"]
            user = User.objects.get(id=user_id)
            refresh.blacklist()
            new_refresh = RefreshToken.for_user(user)
            new_access = str(new_refresh.access_token)

            response = Response({"status": "ok"}, status=status.HTTP_200_OK)
            set_auth_cookies(response, new_access, str(new_refresh))
            return response
        except Exception:
            raise exceptions.AuthenticationFailed(
                "Invalid or expired refresh token.",
                code="unauthenticated",
            )


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        enforce_csrf(request)

        refresh_raw = request.COOKIES.get("refresh_token")
        if refresh_raw:
            try:
                token = RefreshToken(refresh_raw)
                token.blacklist()
            except Exception:
                pass

        response = Response({"status": "ok"}, status=status.HTTP_200_OK)
        clear_auth_cookies(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = Response(
            UserSummarySerializer(request.user).data,
            status=status.HTTP_200_OK,
        )
        set_csrf_cookie(request, response)
        return response
