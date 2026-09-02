"""
PL_SGE - Plataforma Web Integral de Gestion Academica Institucional
Configuracion principal del proyecto Django.
"""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_dotenv(path=BASE_DIR / ".env"):
    """Carga variables desde .env sin dependencias externas.

    Las variables ya presentes en el entorno tienen prioridad, de modo que un
    despliegue puede sobrescribir cualquier valor del archivo.
    """
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv()


def env(key, default=None, cast=str):
    value = os.environ.get(key, default)
    if value is None:
        return None
    if cast is bool:
        return str(value).strip().lower() in ("1", "true", "yes", "on", "si")
    if cast is int:
        return int(value)
    if cast is list:
        return [item.strip() for item in str(value).split(",") if item.strip()]
    return value


# ---------------------------------------------------------------------------
# Seguridad basica
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-pl-sge-cambiar-en-produccion-9f2b1c7a4e")
DEBUG = env("DJANGO_DEBUG", "True", bool)
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", "*", list)
CSRF_TRUSTED_ORIGINS = env(
    "DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000", list
)

# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.humanize",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
]

LOCAL_APPS = [
    "core.users",
    "core.authentication",
    "core.audit",
    "core.institutions",
    "core.configuration",
    "core.academic",
    "core.students",
    "core.teachers",
    "core.evaluations",
    "core.attendance",
    "core.tutoring",
    "core.observer",
    "core.promotion",
    "core.recoveries",
    "core.emphases",
    "core.documents",
    "core.reports",
    "core.agenda",
    "core.classroom",
    "core.elections",
    "core.extensions",
    "core.notifications",
    "core.dashboard",
    "core.pae",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Debe ir despues de la autenticacion: resuelve la institucion activa a
    # partir de la sesion o del usuario, y antes de la auditoria y las vistas.
    "core.institutions.middleware.ActiveInstitutionMiddleware",
    "core.audit.middleware.AuditMiddleware",
    "core.authentication.middleware.TwoFactorMiddleware",
    "core.authentication.middleware.SessionActivityMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.institutions.context_processors.institution",
                "core.configuration.context_processors.navigation",
                "core.notifications.context_processors.notifications",
            ],
            "builtins": ["core.configuration.templatetags.sge"],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Base de datos - PostgreSQL
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "pl_sge"),
        "USER": env("DB_USER", "postgres"),
        "PASSWORD": env("DB_PASSWORD", "postgres"),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": env("DB_CONN_MAX_AGE", 60, int),
        "OPTIONS": {},
    }
}

# Fallback SQLite para desarrollo local sin PostgreSQL: DB_ENGINE=sqlite
if env("DB_ENGINE", "postgresql") == "sqlite":
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "database" / "pl_sge.sqlite3",
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "core.authentication.backends.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internacionalizacion
# ---------------------------------------------------------------------------
LANGUAGE_CODE = env("DJANGO_LANGUAGE", "es-co")
TIME_ZONE = env("DJANGO_TIMEZONE", "America/Bogota")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos estaticos y media
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

# ---------------------------------------------------------------------------
# Sesiones y autenticacion web
# ---------------------------------------------------------------------------
LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/auth/login/"

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_NAME = "plsge_sessionid"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = env("SESSION_COOKIE_AGE", 60 * 60 * 8, int)
SESSION_IDLE_TIMEOUT = env("SESSION_IDLE_TIMEOUT", 60 * 60, int)

CSRF_COOKIE_NAME = "plsge_csrftoken"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"

if not DEBUG:
    SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT", "False", bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "120/min", "user": "1200/min", "login": "10/min"},
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    # El parametro ?format= lo usa PL_SGE para elegir el formato de exportacion
    # (xlsx / csv); se desactiva la negociacion de contenido de DRF sobre el.
    "URL_FORMAT_OVERRIDE": None,
}

if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    )
else:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = ("rest_framework.renderers.JSONRenderer",)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_MINUTES", 60, int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_DAYS", 7, int)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "core.authentication.serializers.PLSGETokenObtainPairSerializer",
}

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env(
    "CORS_ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000", list
)
CORS_ALLOW_ALL_ORIGINS = DEBUG

# ---------------------------------------------------------------------------
# Correo
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = env("EMAIL_PORT", 587, int)
EMAIL_USE_TLS = env("EMAIL_USE_TLS", "True", bool)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "PL_SGE <no-reply@datly.local>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ---------------------------------------------------------------------------
# Parametros funcionales de la plataforma
# ---------------------------------------------------------------------------
PLSGE = {
    # Nombre visible de la aplicacion: titulos de pagina, pantalla de ingreso,
    # pie de pagina y respaldo del nombre institucional en el menu lateral.
    "NAME": "KINDORA",
    "LONG_NAME": "Aplicación de Instituciones Académicas",
    "VERSION": "1.0.0",
    "VENDOR": "Datly",
    "SUPPORT_EMAIL": "soporte@datly.local",
    "OTP_ISSUER": env("OTP_ISSUER", "KINDORA"),
    "PASSWORD_RESET_TIMEOUT_HOURS": 2,
    "MAX_LOGIN_ATTEMPTS": env("MAX_LOGIN_ATTEMPTS", 5, int),
    "LOCKOUT_MINUTES": env("LOCKOUT_MINUTES", 15, int),
    "DEFAULT_PAGE_SIZE": 25,
    "GRADE_DECIMALS": 2,
}

PASSWORD_RESET_TIMEOUT = PLSGE["PASSWORD_RESET_TIMEOUT_HOURS"] * 3600

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name} {message}", "style": "{"},
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "pl_sge.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
    "loggers": {
        "django.db.backends": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
        "pl_sge": {
            "level": "DEBUG" if DEBUG else "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
}
