from .settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",
    }
}

# Disable migration checks for tests
MIGRATION_MODULES = {app: None for app in INSTALLED_APPS if app not in [
    "django.contrib.contenttypes",
    "django.contrib.auth",
]}
