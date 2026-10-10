from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", ".vercel.app"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:5173"])

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
]

LOCAL_APPS = [
    "core",
    "accounts",
    "deposits",
    "ingestion",
    "reports",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "core.middleware.NoStoreCacheMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = []

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        engine="django.db.backends.postgresql",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_table",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG

JWT_COOKIE_SAMESITE = "Lax"
JWT_COOKIE_SECURE = not DEBUG

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.CookieJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "upload": env("UPLOAD_THROTTLE", default="30/hour"),
        "login": env("LOGIN_THROTTLE", default="5/minute"),
    },
}

JWT_ACCESS_MINUTES = env.int("JWT_ACCESS_MINUTES", default=30)
JWT_REFRESH_DAYS = env.int("JWT_REFRESH_DAYS", default=7)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=JWT_ACCESS_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=JWT_REFRESH_DAYS),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

EXTRACTION_STRATEGY = env("EXTRACTION_STRATEGY", default="ocr_text")
GROQ_API_KEY = env("GROQ_API_KEY", default="")
GROQ_VISION_MODEL = env("GROQ_VISION_MODEL", default="qwen/qwen3.8-27b")
GROQ_TEXT_MODEL = env("GROQ_TEXT_MODEL", default="qwen/qwen3.8-27b")
GROQ_STRUCTURED_MODE = env("GROQ_STRUCTURED_MODE", default="json_schema_strict")
GROQ_MAX_COMPLETION_TOKENS = env.int("GROQ_MAX_COMPLETION_TOKENS", default=3000)
GROQ_MAX_RETRY_WAIT_S = env.int("GROQ_MAX_RETRY_WAIT_S", default=20)
GROQ_REASONING_EFFORT = env("GROQ_REASONING_EFFORT", default=None)
OCR_SPACE_API_KEY = env("OCR_SPACE_API_KEY", default="")
OCR_SPACE_ENGINE = env.int("OCR_SPACE_ENGINE", default=3)
OCR_SPACE_TIMEOUT_S = env.int("OCR_SPACE_TIMEOUT_S", default=30)
LLM_MODE = env("LLM_MODE", default="live")
LLM_TIMEOUT_S = env.int("LLM_TIMEOUT_S", default=60)
MAX_UPLOAD_MB = env.int("MAX_UPLOAD_MB", default=4)
UPLOAD_THROTTLE = env("UPLOAD_THROTTLE", default="30/hour")
AUTO_SAVE_ENABLED = env.bool("AUTO_SAVE_ENABLED", default=False)
T_AUTO = env.float("T_AUTO", default=0.92)
T_CONFIRM = env.float("T_CONFIRM", default=0.60)
SCORE_W_LLM = env.float("SCORE_W_LLM", default=0.20)
SCORE_W_TYPE = env.float("SCORE_W_TYPE", default=0.25)
SCORE_W_NAME = env.float("SCORE_W_NAME", default=0.20)
SCORE_W_WEIGHT = env.float("SCORE_W_WEIGHT", default=0.25)
SCORE_W_DATE = env.float("SCORE_W_DATE", default=0.10)
MATCH_MIN_TYPE = env.float("MATCH_MIN_TYPE", default=0.75)
MATCH_MIN_NASABAH = env.float("MATCH_MIN_NASABAH", default=0.85)
MATCH_AMBIGUITY_MARGIN = env.float("MATCH_AMBIGUITY_MARGIN", default=0.05)
MAX_WEIGHT_KG_PER_ROW = env.float("MAX_WEIGHT_KG_PER_ROW", default=200.0)
