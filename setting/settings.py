"""
Django settings for sistema_facturacion project.
"""

import os
from pathlib import Path
from corsheaders.defaults import default_headers
from dotenv import load_dotenv

# ==============================================================================
# RUTAS BASE
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga las variables del archivo .env en la raíz del proyecto
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [value.strip() for value in os.environ.get(name, default).split(',') if value.strip()]


# ==============================================================================
# SEGURIDAD
# ==============================================================================

DEBUG = env_bool('DEBUG', True)

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-set-secret-key-in-env'
    else:
        raise RuntimeError('SECRET_KEY is required when DEBUG=False.')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')


# ==============================================================================
# APLICACIONES INSTALADAS
# ==============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceros
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',

    # Propias
    'facturacion',
]


# ==============================================================================
# MIDDLEWARE
# ==============================================================================

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',          # ← Debe ir primero
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'facturacion.api.middleware.CompanyContextMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ==============================================================================
# URLS Y WSGI
# ==============================================================================

ROOT_URLCONF = 'setting.urls'

WSGI_APPLICATION = 'setting.wsgi.application'


# ==============================================================================
# TEMPLATES
# ==============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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


# ==============================================================================
# BASE DE DATOS
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':     os.environ.get('DB_NAME', 'facturacion'),
        'USER':     os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST':     os.environ.get('DB_HOST', 'localhost'),
        'PORT':     os.environ.get('DB_PORT', '5432'),
    }
}


# ==============================================================================
# DJANGO REST FRAMEWORK
# ==============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'facturacion.api.pagination.OptionalPageNumberPagination',
    'PAGE_SIZE': int(os.environ.get('API_PAGE_SIZE', '50')),
    'EXCEPTION_HANDLER': 'facturacion.api.exceptions.normalized_exception_handler',
}


# ==============================================================================
# CORS (para React en desarrollo)
# ==============================================================================

CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', 'https://7l51msx7-8000.use2.devtunnels.ms,https://7l51msx7-3000.use2.devtunnels.ms')

CORS_ALLOW_ALL_ORIGINS = env_bool('CORS_ALLOW_ALL_ORIGINS', True)

CORS_ALLOW_HEADERS = list(default_headers) + [
    'x-company-id',
]


# ==============================================================================
# VALIDACIÓN DE CONTRASEÑAS
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ==============================================================================
# INTERNACIONALIZACIÓN
# ==============================================================================

LANGUAGE_CODE = 'es-419'   # Español latinoamericano

TIME_ZONE = 'America/Santo_Domingo'

USE_I18N = True

USE_TZ = True


# ==============================================================================
# ARCHIVOS ESTÁTICOS Y MEDIA
# ==============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ==============================================================================
# OTROS
# ==============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
    SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', True)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'


# ==============================================================================
# CELERY / REDIS
# ==============================================================================

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_POOL = os.environ.get('CELERY_WORKER_POOL', 'solo' if os.name == 'nt' else 'prefork')
CELERY_WORKER_CONCURRENCY = int(os.environ.get('CELERY_WORKER_CONCURRENCY', '1' if os.name == 'nt' else '4'))
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.environ.get('CELERY_WORKER_PREFETCH_MULTIPLIER', '1'))
CELERY_TASK_ACKS_LATE = os.environ.get('CELERY_TASK_ACKS_LATE', 'True') == 'True'
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_DEFAULT_QUEUE = 'ecf.default'
CELERY_TASK_ROUTES = {
    'facturacion.ecf.tasks.xml.generate_xml': {'queue': 'ecf.xml'},
    'facturacion.ecf.tasks.signing.sign_xml': {'queue': 'ecf.signing'},
    'facturacion.ecf.tasks.dgii.submit_dgii': {'queue': 'ecf.dgii'},
    'facturacion.ecf.tasks.dgii.check_status': {'queue': 'ecf.status'},
    'facturacion.ecf.tasks.dgii.retry_submission': {'queue': 'ecf.retry'},
}
ECF_TASK_MAX_RETRIES = int(os.environ.get('ECF_TASK_MAX_RETRIES', '5'))
ECF_TASK_RETRY_BACKOFF_SECONDS = int(os.environ.get('ECF_TASK_RETRY_BACKOFF_SECONDS', '60'))
ECF_TASK_STATUS_CHECK_DELAY_SECONDS = int(os.environ.get('ECF_TASK_STATUS_CHECK_DELAY_SECONDS', '120'))


# ==============================================================================
# DGII E-CF
# ==============================================================================

ECF_DEFAULT_ITBIS_RATE = os.environ.get('ECF_DEFAULT_ITBIS_RATE', '18.00')
ECF_DEFAULT_INCOME_TYPE = os.environ.get('ECF_DEFAULT_INCOME_TYPE', '01')
ECF_CERTIFICATE_PATH = os.environ.get('ECF_CERTIFICATE_PATH')
ECF_CERTIFICATE_PASSWORD = os.environ.get('ECF_CERTIFICATE_PASSWORD')
ECF_ALLOW_GLOBAL_CERTIFICATE_FALLBACK = os.environ.get(
    'ECF_ALLOW_GLOBAL_CERTIFICATE_FALLBACK',
    'False',
) == 'True'
ECF_ALLOW_DEV_SELF_SIGNED_CERT = os.environ.get(
    'ECF_ALLOW_DEV_SELF_SIGNED_CERT',
    'True' if DEBUG else 'False',
) == 'True'
ECF_DEV_CERTIFICATE_PASSWORD = os.environ.get('ECF_DEV_CERTIFICATE_PASSWORD', 'dev-ecf-password')
ECF_DGII_ENVIRONMENT = os.environ.get('ECF_DGII_ENVIRONMENT', 'testing')
ECF_DGII_MOCK_ENABLED = os.environ.get('ECF_DGII_MOCK_ENABLED', 'True' if DEBUG else 'False') == 'True'
ECF_DGII_AUTH_TOKEN = os.environ.get('ECF_DGII_AUTH_TOKEN')
ECF_DGII_TIMEOUT = int(os.environ.get('ECF_DGII_TIMEOUT', '30'))
ECF_DGII_RETRIES = int(os.environ.get('ECF_DGII_RETRIES', '3'))
ECF_DGII_RETRY_BACKOFF = float(os.environ.get('ECF_DGII_RETRY_BACKOFF', '0.5'))
ECF_DGII_VERIFY_TLS = os.environ.get('ECF_DGII_VERIFY_TLS', 'True') == 'True'
ECF_DGII_REST_BASE_URLS = {
    'testing': {
        'auth': os.environ.get('ECF_DGII_TEST_AUTH_BASE_URL'),
        'reception': os.environ.get('ECF_DGII_TEST_RECEPTION_BASE_URL'),
        'status': os.environ.get('ECF_DGII_TEST_STATUS_BASE_URL'),
        'trackids': os.environ.get('ECF_DGII_TEST_TRACKIDS_BASE_URL'),
    },
    'certification': {
        'auth': os.environ.get('ECF_DGII_CERT_AUTH_BASE_URL'),
        'reception': os.environ.get('ECF_DGII_CERT_RECEPTION_BASE_URL'),
        'status': os.environ.get('ECF_DGII_CERT_STATUS_BASE_URL'),
        'trackids': os.environ.get('ECF_DGII_CERT_TRACKIDS_BASE_URL'),
    },
    'production': {
        'auth': os.environ.get('ECF_DGII_PROD_AUTH_BASE_URL'),
        'reception': os.environ.get('ECF_DGII_PROD_RECEPTION_BASE_URL'),
        'status': os.environ.get('ECF_DGII_PROD_STATUS_BASE_URL'),
        'trackids': os.environ.get('ECF_DGII_PROD_TRACKIDS_BASE_URL'),
    },
}
ECF_DGII_SOAP_WSDLS = {
    'testing': {
        'reception': os.environ.get('ECF_DGII_TEST_RECEPTION_WSDL'),
        'status': os.environ.get('ECF_DGII_TEST_STATUS_WSDL'),
        'trackids': os.environ.get('ECF_DGII_TEST_TRACKIDS_WSDL'),
    },
    'certification': {
        'reception': os.environ.get('ECF_DGII_CERT_RECEPTION_WSDL'),
        'status': os.environ.get('ECF_DGII_CERT_STATUS_WSDL'),
        'trackids': os.environ.get('ECF_DGII_CERT_TRACKIDS_WSDL'),
    },
    'production': {
        'reception': os.environ.get('ECF_DGII_PROD_RECEPTION_WSDL'),
        'status': os.environ.get('ECF_DGII_PROD_STATUS_WSDL'),
        'trackids': os.environ.get('ECF_DGII_PROD_TRACKIDS_WSDL'),
    },
}
ECF_DGII_SOAP_OPERATIONS = {
    'submit': os.environ.get('ECF_DGII_SOAP_SUBMIT_OPERATION', 'RecepcionECF'),
    'status': os.environ.get('ECF_DGII_SOAP_STATUS_OPERATION', 'ConsultaResultado'),
    'trackids': os.environ.get('ECF_DGII_SOAP_TRACKIDS_OPERATION', 'ConsultaTrackIds'),
}
ECF_AUTO_CREATE_ENABLED = os.environ.get('ECF_AUTO_CREATE_ENABLED', 'True') == 'True'
ECF_AUTO_ENQUEUE_ENABLED = os.environ.get('ECF_AUTO_ENQUEUE_ENABLED', 'True') == 'True'
ECF_DEFAULT_TYPE = os.environ.get('ECF_DEFAULT_TYPE', '32')
ECF_AUTO_CREATE_INVOICE_STATUSES = tuple(
    value.strip()
    for value in os.environ.get('ECF_AUTO_CREATE_INVOICE_STATUSES', 'paid,pending').split(',')
    if value.strip()
)


# ==============================================================================
# LOGGING
# ==============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s %(ecf)s',
        },
        'standard': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'ecf_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'structured',
        },
    },
    'loggers': {
        'facturacion.ecf.tasks': {
            'handlers': ['ecf_console'],
            'level': os.environ.get('ECF_TASK_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
    },
}
