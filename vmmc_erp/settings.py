import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add apps directory to sys.path
APPS_DIR = BASE_DIR / 'apps'
sys.path.insert(0, str(APPS_DIR))

# Load environment variables (.env in project root or /etc/csvsittech/.env)
system_env = Path('/etc/csvsittech/.env')
if system_env.exists():
    load_dotenv(system_env)
else:
    load_dotenv(BASE_DIR / '.env')

DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-vmmc-erp-dev-key'
    else:
        raise ValueError("SECRET_KEY environment variable is required in production.")

# Allowed Hosts & CSRF Origins for csvsittech.in
allowed_hosts_env = os.getenv(
    'ALLOWED_HOSTS',
    'csvsittech.in,www.csvsittech.in,127.0.0.1,localhost'
)
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]

csrf_origins_env = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'https://csvsittech.in,https://www.csvsittech.in,http://127.0.0.1:8000,http://localhost:8000'
)
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins_env.split(',') if origin.strip()]

# Security headers & SSL
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 't')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    origin for origin in CSRF_TRUSTED_ORIGINS if origin.startswith(('http://', 'https://'))
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party packages
    'rest_framework',
    'corsheaders',

    # Local ERP apps
    'apps.users',
    'apps.core',
    'apps.patients',
    'apps.lab',
    'apps.ot',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'vmmc_erp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'vmmc_erp.wsgi.application'
ASGI_APPLICATION = 'vmmc_erp.asgi.application'

# ============================================================
# Database Configuration (PostgreSQL / SQLite)
# ============================================================

import dj_database_url

DATABASE_URL = os.getenv('DATABASE_URL')
USE_POSTGRES = os.getenv('USE_POSTGRES', '').lower() in ('true', '1', 't')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif USE_POSTGRES:
    DATABASES = {
        'default': {
            'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
            'NAME': os.getenv('DB_NAME', os.getenv('PGDATABASE', 'csvsittech_db')),
            'USER': os.getenv('DB_USER', os.getenv('PGUSER', 'csvsittech_user')),
            'PASSWORD': os.getenv('DB_PASSWORD', os.getenv('PGPASSWORD', '')),
            'HOST': os.getenv('DB_HOST', os.getenv('PGHOST', '127.0.0.1')),
            'PORT': os.getenv('DB_PORT', os.getenv('PGPORT', '5432')),
            'CONN_MAX_AGE': 600,
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.config(
            default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
            conn_max_age=600,
        )
    }
    if 'sqlite' in DATABASES['default'].get('ENGINE', ''):
        DATABASES['default']['OPTIONS'] = {'timeout': 30}

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Authentication URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
WHITENOISE_MANIFEST_STRICT = False

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
}

# ============================================================
# Logging Configuration
# ============================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
