import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
INSTALLED_APPS = ["django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "mozilla_django_oidc", "core"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "agenda_project.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "agenda_project.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "agenda", "USER": "agenda", "PASSWORD": os.environ["DB_PASSWORD"], "HOST": os.environ["DB_HOST"], "PORT": "5432"}}
AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTHENTICATION_BACKENDS = ("agenda_project.oidc_backend.KeycloakBackend", "django.contrib.auth.backends.ModelBackend")
LOGIN_URL = "oidc_authentication_init"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
OIDC_RP_CLIENT_ID = "agenda"
OIDC_RP_CLIENT_SECRET = os.environ["OIDC_CLIENT_SECRET"]
OIDC_RP_USERNAME_CLAIM = "preferred_username"
# O Keycloak assina os ID Tokens com RSA; a biblioteca assume HS256 se não
# informarmos o algoritmo explicitamente.
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_OP_AUTHORIZATION_ENDPOINT = "http://localhost:8080/realms/sso-platform/protocol/openid-connect/auth"
OIDC_OP_TOKEN_ENDPOINT = "http://keycloak:8080/realms/sso-platform/protocol/openid-connect/token"
OIDC_OP_USER_ENDPOINT = "http://keycloak:8080/realms/sso-platform/protocol/openid-connect/userinfo"
OIDC_OP_JWKS_ENDPOINT = "http://keycloak:8080/realms/sso-platform/protocol/openid-connect/certs"
OIDC_RP_SCOPES = "openid profile email"
OIDC_OP_LOGOUT_URL_METHOD = "agenda_project.oidc.logout_url"
# Usado pelo KeycloakBackend para conceder a role da app via Admin API
# quando um usuário novo chega pelo login social do Google.
OIDC_OP_ADMIN_API_BASE = "http://keycloak:8080/admin/realms/sso-platform"
