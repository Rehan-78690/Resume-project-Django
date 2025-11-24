# resume_builder/settings.py

from pathlib import Path
import os
import environ
from datetime import timedelta

# ========== BASE CONFIG ==========
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)

# Load .env file
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

DEBUG = env("DEBUG", default=True)
SECRET_KEY = env("SECRET_KEY", default="dev-secret-key-change-this")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])


# ========== INSTALLED APPS ==========
INSTALLED_APPS = [
    # Django built-ins
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Third-party
    'rest_framework',
    'rest_framework.authtoken',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',

    # Local apps
    'accounts',
]

SITE_ID = 1


# ========== MIDDLEWARE ==========
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ========== URL CONFIG ==========
ROOT_URLCONF = 'resume_builder.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # You can add HTML templates later if needed
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',  # REQUIRED for allauth
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'resume_builder.wsgi.application'


# ========== DATABASE ==========
# Local development uses SQLite
DATABASES = {
    'default': {
        'ENGINE': env("DB_ENGINE", default="django.db.backends.sqlite3"),
        'NAME': env("DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
        'USER': env("DB_USER", default=""),
        'PASSWORD': env("DB_PASSWORD", default=""),
        'HOST': env("DB_HOST", default=""),
        'PORT': env("DB_PORT", default=""),
    }
}


# ========== AUTH MODEL ==========
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "optional"


# ========== REST FRAMEWORK + JWT ==========
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}


# ========== PASSWORD VALIDATORS ==========
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]


# ========== INTERNATIONALIZATION ==========
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ========== STATIC & MEDIA ==========
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ========== DEFAULT PRIMARY KEY ==========
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
