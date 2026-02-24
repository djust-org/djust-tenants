"""Django settings for djust-tenants tests."""

SECRET_KEY = "test-secret-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "djust_tenants",
    "tests.testapp",  # Test app with models
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "djust_tenants.middleware.TenantMiddleware",  # Tenant middleware
]

ROOT_URLCONF = "tests.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Tenant configuration
DJUST_TENANTS = {
    "RESOLVER": "subdomain",
    "MAIN_DOMAIN": "example.com",
    "SUBDOMAIN_EXCLUDE": ["www", "api", "admin"],
    "REQUIRED": False,
    "CONTEXT_NAME": "tenant",
}

USE_TZ = True
