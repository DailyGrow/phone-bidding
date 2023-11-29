from .base import *

DEBUG = config('DEBUG', cast=bool)
ALLOWED_HOSTS = ['ip-address', 'www.your-website.com']

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}
]

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': config('DB_NAME'),
#         'USER': config('DB_USER'),
#         'PASSWORD': config('DB_PASSWORD'),
#         'HOST': config('DB_HOST'),
#         'PORT': ''
#     }
# }

import pymysql
pymysql.version_info = (1, 4, 6, 'final', 0)
pymysql.install_as_MySQLdb()

if os.getenv('GAE_APPLICATION',None):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'dev',
            'USER': 'root',
            # 'PASSWORD': '',
            'HOST': '/cloudsql/db-group8-401802:us-west1:neu-test-db',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'dev',
            'USER': 'root',
            # 'PASSWORD': '',
            'HOST': '35.233.133.184',
            'PORT': '3306'
        }
    }
# [END_DB_SETUP]

stripe_live_mode = False
STRIPE_PUBLIC_KEY = config('STRIPE_LIVE_PUBLIC_KEY', default=None)
STRIPE_SECRET_KEY = config('STRIPE_LIVE_SECRET_KEY', default=None)