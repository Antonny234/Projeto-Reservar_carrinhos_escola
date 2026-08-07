from pathlib import Path
import os
import dotenv
from dotenv import load_dotenv
import dj_database_url  # Para conectar ao PostgreSQL via DATABASE_URL (Railway)

load_dotenv(override=False)

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

dotenv.load_dotenv(os.path.join(BASE_DIR, '.env'))

DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['*','.railway.app','observing-underwent-rehydrate.ngrok-free.dev', 'localhost', '127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'reservas',
    'django_select2',
]

# Só adiciona sslserver se o pacote estiver instalado (local)
try:
    import sslserver
    INSTALLED_APPS += ['sslserver']
except ImportError:
    pass

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'configuracao.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR,'reservas','templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'configuracao.wsgi.application'

CSRF_TRUSTED_ORIGINS = [
    'http://localhost',
    'http://127.0.0.1',
    'http://seusite.escola.local',
    'http://192.168.1.100',
    'https://*.up.railway.app',
    'http://lvh.me:8000',
    'https://*.railway.app',
    'https://projeto-reservarcarrinhosescola-production-0586.up.railway.app',
    'https://observing-underwent-rehydrate.ngrok-free.dev',
]
render_host = os.getenv('RENDER_EXTERNAL_HOSTNAME', '')
if render_host:
    CSRF_TRUSTED_ORIGINS.append(f'https://{render_host}')

# ─── BANCO DE DADOS ─────────────────────────────────────────────
# Se a variável DATABASE_URL existir (Railway / produção), usa PostgreSQL.
# Caso contrário, usa SQLite3 local para desenvolvimento.
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Railway / Produção → PostgreSQL
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,          # Mantém conexão aberta por 10 min
            conn_health_checks=True,   # Verifica se a conexão está saudável
        )
    }
else:
    # Desenvolvimento local → SQLite3
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

# ─── SEGURANÇA PARA PRODUÇÃO ────────────────────────────────────
# Segurança SSL/HTTPS:
# SECURE_PROXY_SSL_HEADER → Confia no header HTTP_X_FORWARDED_PROTO enviado
#   pelo proxy reverso (Railway/Nginx) para saber se a requisição veio via HTTPS.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# SECURE_SSL_REDIRECT → Redireciona HTTP para HTTPS automaticamente.
# Só ativo em produção (quando DEBUG=False) para não atrapalhar localhost.
SECURE_SSL_REDIRECT = not DEBUG

# SESSION_COOKIE_SECURE / CSRF_COOKIE_SECURE → Só envia cookies
#   de sessão e CSRF por HTTPS (evita roubo de sessão em redes abertas).
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# SECURE_HSTS_* → Força o navegador a sempre usar HTTPS por 1 ano.
#   Isso evita ataques de downgrade (homem-no-meio).
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# SECURE_CONTENT_TYPE_NOSNIFF → Impede o navegador de "adivinhar"
#   o tipo MIME de arquivos (evita ataques de MIME sniffing).
SECURE_CONTENT_TYPE_NOSNIFF = True

# X_FRAME_OPTIONS → Impede que o site seja carregado dentro de iframes
#   de outros sites (evita clickjacking).
X_FRAME_OPTIONS = 'DENY'

# SECURE_BROWSER_XSS_FILTER → Ativa o filtro XSS embutido do navegador.
SECURE_BROWSER_XSS_FILTER = True

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
LOGIN_URL = '/entrar/'

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'reservas', 'static')]
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

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
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# ─── E-MAIL (Gmail) ─────────────────────────────────────────────
DEFAULT_FROM_EMAIL = 'onboarding@resend.dev'