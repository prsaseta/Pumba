"""
Django settings for pumba project.

Generated by 'django-admin startproject' using Django 2.0.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
import django_heroku
import cloudinary

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'imc8remwl2vmevm**i34+($!u5=dt7sn_=&p_-$3rq$k5c#opk'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

CHEATS_ENABLED = False

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'authentication.apps.AuthenticationConfig',
    'game.apps.GameConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'mathfilters',
    'cloudinary'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]

ROOT_URLCONF = 'pumba.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'authentication', 'static', 'authentication'),
                os.path.join(BASE_DIR, 'game', 'static', 'game'),
                os.path.join(BASE_DIR, 'pumba', 'static')],
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

WSGI_APPLICATION = 'pumba.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.postgresql',
#        'NAME': 'pumba',
#        'USER': 'pumba',
#        'PASSWORD': 'pumba',
#        'HOST': 'localhost',
#        'PORT': '',
#    }
#}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
      
        'TEST':{
            'NAME':os.path.join(BASE_DIR,'db_test.sqlite3'),
        }

      
    }
}

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = [BASE_DIR + "/locales"]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (BASE_DIR, os.path.join('pumba/static'))

# Configuración de correo
# Uso un servicio externo
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_HOST_USER = 'EDPVincent'
EMAIL_HOST_PASSWORD = 'PumbaPumba8'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# Esto activa o desactiva la necesidad de usar el correo para registrarse
IS_USING_EMAIL_VERIFICATION_FOR_REGISTRY = True

# URL base para los correos de verificación
if os.environ.get('DEPLOYMENT_URL') is not None:
    VERIFICATION_MAIL_URL = os.environ.get('DEPLOYMENT_URL')
else:
    VERIFICATION_MAIL_URL = "http://localhost:8000"

# Channels
ASGI_APPLICATION = "pumba.routing.application"

heroku_redis = None
if os.environ.get('REDIS_URL') is not None:
    heroku_redis = os.environ.get('REDIS_URL')
else:
    heroku_redis = ('127.0.0.1', 6379)

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [heroku_redis],
        },
    },
}

# Por si intentas acceder sin permisos, que te redirija
LOGIN_URL = "/authentication/login"

# Ngrok
ALLOWED_HOSTS = ["*"]

# Para enviarme el feedback por correo
FEEDBACK_MAIL_ADDRESS = "rodriguezsaseta@gmail.com"

# Logging en Heroku
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'ERROR'),
        },
    },
}

# Credenciales de Cloudinary
cloudinary.config( 
  cloud_name = "hjujot11s", 
  api_key = "372813674549718", 
  api_secret = "0D8vxpDeuZuRG10IA1edc9XpJTU",
  secure = True
)

django_heroku.settings(locals())