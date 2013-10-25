#!/bin/sh -ex
bogus=''' '
export PYTHONPATH=.
export DJANGO_SETTINGS_MODULE=run_redisboard
secret() {
    tr -cd "[:alnum:]" < /dev/urandom | head -c ${1:-8}
}
chmod +x run_redisboard.py
if [ ! -e .redisboard.venv ]; then
    virtualenv .redisboard.venv
    .redisboard.venv/bin/pip install Django django-redisboard
fi
. .redisboard.venv/bin/activate
if [ ! -e .redisboard.secret ]; then
    echo $(secret 32) > .redisboard.secret
fi
python run_redisboard.py $*
exit
'''

import os
import sys
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '.redisboard.sqlite',
    }
}
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'redisboard',
)
MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)
SECRET_KEY = open('.redisboard.secret').read().strip()
ROOT_URLCONF = 'run_redisboard'
STATIC_URL = '/static/'
ALLOWED_HOSTS = ['*']
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s | %(name)s - %(message)s',
            'datefmt': "%d/%b/%Y %H:%M:%S",
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        "": {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False
        },
    }
}
from django.conf import settings
if not settings.configured:
    settings.configure(**{k: v for k, v in globals().items() if k.isupper()})

from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()
urlpatterns = patterns("",
    url(r"^static/(?P<path>.*)$", 'django.contrib.staticfiles.views.serve', {'insecure': True}),
    url(r"^", include(admin.site.urls)),
)


if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    if not os.path.exists('.redisboard.sqlite'):
        execute_from_command_line(['run_redisboard', 'syncdb', '--noinput'])
        from django.contrib.auth.models import User
        u = User.objects.create(username='redisboard', is_superuser=True, is_staff=True, is_active=True)
        pwd = os.urandom(8).encode('hex')
        u.set_password(pwd)
        u.save()
        print "="*80
        print """   Credentials:
            USERNAME: redisboard
            PASSWORD: %s""" % pwd
        print "="*80
        from redisboard.models import RedisServer
        RedisServer.objects.create(label="localhost", hostname="127.0.0.1")
    execute_from_command_line(['run_redisboard', 'runserver', '--noreload'] + (sys.argv[1:] if len(sys.argv) > 1 else ['0:8000']))
