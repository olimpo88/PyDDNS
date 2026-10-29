"""
Base Django settings shared by all environments.
Environment-specific overrides live in development.py / production.py.
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('DJANGO_SECRET_KEY environment variable is required')

# Default closed; environment modules relax this where appropriate.
DEBUG = False
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]


LOGIN_URL = '/common/login/'


ENABLE_REST_API = os.environ.get('ENABLE_REST_API', '0').lower() in ('1', 'true', 'yes')

INSTALLED_APPS = [
    # Subclass of AdminConfig that swaps in an admin site honouring 2FA.
    'common.adminconfig.PyDDNSAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',
    'common',
    'pyddns',
]

if ENABLE_REST_API:
    INSTALLED_APPS += [
        'rest_framework',
        'rest_framework.authtoken',
        'api',
    ]

    REST_FRAMEWORK = {
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'rest_framework.authentication.TokenAuthentication',
            'rest_framework.authentication.SessionAuthentication',
        ],
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.IsAuthenticated',
        ],
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
        'PAGE_SIZE': 20,
    }

MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'common.middleware.TwoFactorMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'pyddns.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            'common/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
                'common.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'pyddns.wsgi.application'


# Persistent connections cap connection churn under load. Each gunicorn
# worker keeps its DB connection alive for up to DB_CONN_MAX_AGE seconds
# instead of opening + closing one per request. With CONN_HEALTH_CHECKS
# Django pings the connection at the start of each request and reconnects
# transparently if the server has dropped it (typical on idle timeouts).
# Set DB_CONN_MAX_AGE=0 to revert to the per-request default.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': '5432',
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
        'CONN_HEALTH_CHECKS': True,
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.RemoteUserBackend',
    'django.contrib.auth.backends.ModelBackend',
)


# Internationalization
#
# DJANGO_LANGUAGE_CODE controls the i18n mode:
#   - empty / unset → international mode: LocaleMiddleware auto-detects from
#     Accept-Language and the user can switch via the language picker. EN
#     is the fallback when nothing matches.
#   - non-empty (e.g. "es", "fr", "pt-br") → locked mode: every page is
#     served in that language. The picker is hidden. Other locale URLs
#     (/de/..., /ja/...) return 404.
_LOCKED = (os.environ.get('DJANGO_LANGUAGE_CODE') or '').strip().lower()
LANGUAGE_LOCKED = bool(_LOCKED)
LANGUAGE_CODE = _LOCKED if LANGUAGE_LOCKED else 'en'
TIME_ZONE = os.environ.get('DJANGO_TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'

DNS_HOST = os.environ.get('DNS_HOST')
DNS_API_PORT = os.environ.get('DNS_API_PORT')
DNS_SHARED_SECRET = os.environ.get('DNS_SHARED_SECRET')
DNS_ALLOW_AGENT = os.environ.get('DNS_ALLOW_AGENT')
# Shown in the footer and on the login page; bump together with the git tag.
PYDDNS_VERSION = '2.1.0'

DNS_DOMAIN = os.environ.get('DNS_DOMAIN')
OWN_ADMIN = os.environ.get('OWN_ADMIN')

# ── Email ─────────────────────────────────────────────────────────────────
# When EMAIL_HOST is set, real SMTP is used; otherwise emails are written
# to the container stderr (console backend), which is convenient for dev
# and harmless in production deployments that don't need notifications.
EMAIL_HOST = os.environ.get('EMAIL_HOST', '').strip()
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '1').lower() in ('1', 'true', 'yes')
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', '0').lower() in ('1', 'true', 'yes')
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '10'))
DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_FROM', f'PyDDNS <noreply@{DNS_DOMAIN or "localhost"}>')

if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# When False, the self-service password-reset flow (URLs + login link)
# is hidden and only admins can change passwords via the Users page.
ALLOW_PASSWORD_RESET = os.environ.get('ALLOW_PASSWORD_RESET', '1').lower() in ('1', 'true', 'yes')

# Two-factor authentication (TOTP). Opt-in for every user from /common/2fa/.
# ADMIN_FORCE_2FA=1 makes it mandatory for staff/superusers: right after the
# password step they are redirected to enrol and cannot use the rest of the
# app until they do. Default 0, so enabling nothing locks out existing admins.
ADMIN_FORCE_2FA = os.environ.get('ADMIN_FORCE_2FA', '0').lower() in ('1', 'true', 'yes')
# Label shown by authenticator apps next to the account name.
OTP_TOTP_ISSUER = f'PyDDNS ({DNS_DOMAIN})' if DNS_DOMAIN else 'PyDDNS'
# django-otp throttles wrong codes per device (exponential back-off) by default.

# Used by password-reset emails to build absolute links. Falls back to
# DNS_DOMAIN; tweakable per-deployment if you serve the UI from a different
# hostname than the DDNS zone.
SITE_URL = os.environ.get('SITE_URL', f'https://{DNS_DOMAIN or "localhost"}').rstrip('/')


from django.utils.translation import gettext_lazy as _

_ALL_LANGUAGES = (
    ('es', _('Spanish')),
    ('en', _('English')),
    ('pt-br', _('Brazilian Portuguese')),
    ('fr', _('French')),
    ('de', _('German')),
    ('ru', _('Russian')),
    ('ja', _('Japanese')),
    ('zh-hans', _('Simplified Chinese')),
)

if LANGUAGE_LOCKED:
    # Accept exact match first ('es' or 'pt-br'); fall back to the base
    # language part so 'es-es', 'pt-BR', 'fr-FR' all resolve sensibly.
    _matched = [(c, n) for c, n in _ALL_LANGUAGES if c == LANGUAGE_CODE]
    if not _matched:
        _base = LANGUAGE_CODE.split('-')[0]
        _matched = [(c, n) for c, n in _ALL_LANGUAGES if c == _base]
    if not _matched:
        raise RuntimeError(
            f'DJANGO_LANGUAGE_CODE={LANGUAGE_CODE!r} is not a supported locale. '
            f'Supported: {[c for c, _n in _ALL_LANGUAGES]}'
        )
    LANGUAGE_CODE = _matched[0][0]  # canonicalize to the entry's own code
    LANGUAGES = tuple(_matched)
else:
    LANGUAGES = _ALL_LANGUAGES

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
