"""
Django settings for myblog project.

Generated by 'django-admin startproject' using Django 1.10.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""
# choose settings between Developement and Deploy
import os
import platform

node = platform.node()
print(node)
dev_machines = ('cheng-cx','cheng-cx.local')

if node in dev_machines:
    # folder QinggangManageSys
    QinggangManageSys = os.path.dirname(os.path.dirname(__file__))
    # project dir, contains static and media folder under DEV environment
    PROJECT_DIR = os.path.dirname(QinggangManageSys)
    DEBUG = True
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'qinggang',
            'USER': 'root',
            'PASSWORD': '123456',
            'HOST': '202.204.54.212',
            # 'HOST': 'localhost',
            'PORT': '3306',
        },
        'l2own': {
            'ENGINE': 'django.db.backends.oracle',
            'NAME':'orcl',
            'USER': 'qg_user',
            'PASSWORD': '123456',
            'HOST': '202.204.54.212',
            'PORT': '1521',
        },
        'sale': {
            'ENGINE': 'django.db.backends.oracle',
            'NAME':'orcl',
            'USER': 'meskc',
            'PASSWORD': '123456',
            'HOST': '202.204.54.212',
            'PORT': '1521',
        },
    }
    print(PROJECT_DIR)
    STATIC_ROOT = os.path.join(PROJECT_DIR, 'static')
    STATIC_URL = '/static/'
    MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')
    print(MEDIA_ROOT)
    MEDIA_URL = '/media/'
    STATICFILES_DIRS = (
        os.path.join(PROJECT_DIR, 'static'),
    )
    TEMPLATE_DIRS = [os.path.join(QinggangManageSys, 'templates')]
    ALLOWED_HOSTS = ['*']
else:
    DEBUG = True
    DATABASES = {
        'l2own': {
            'ENGINE': 'django.db.backends.oracle',
            'NAME':'orcl',
            'USER': 'qg_user',
            'PASSWORD': '123456',
            'HOST': '202.204.54.212',
            'PORT': '1521',
        },
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'qinggang',
            'USER': 'root',
            'PASSWORD': '123456',
            'HOST': '202.204.54.212',
            'PORT': '3306',
        },
        'mes': {
            'ENGINE': 'django.db.backends.oracle',
            'NAME': 'mesdb2',#sid:mesdb2;service:mesdb
            'USER': 'xx_query',
            'PASSWORD': 'xxx',
            'HOST': 'xx.30.xx.17',
            'PORT': '1521',
        },
        'l2': {
            'ENGINE': 'django.db.backends.oracle',
            'NAME': 'qgil2db',
            'USER': 'xx_query',
            'PASSWORD': 'xxx',
            'HOST': 'xx.30.xx.17',
            'PORT': '1521',
        },
        'sale': {
            'ENGINE': 'django.db.backends.oracle',
            'NAME':'orcl',
            'USER': 'meskc',
            'PASSWORD': '123456',
            'HOST': '202.204.54.212',
            'PORT': '1521',
        },
    }
    PROJECT_DIR = '/home/maksim/venv/qinggang/managesys'
    MEDIA_ROOT = '/home/maksim/venv/qinggang/media/'
    MEDIA_URL = '/media/'
    STATIC_ROOT = '/home/maksim/venv/qinggang/static/'
    STATIC_URL = '/static/'

    STATICFILES_DIRS = (
        os.path.join(PROJECT_DIR, 'static'),
    )

    TEMPLATE_DIRS = (
        os.path.join(PROJECT_DIR, 'templates'),
    )

    ALLOWED_HOSTS = [
        '*',
    ]

    # # cache entire site
    # MIDDLEWARE_CLASSES_ADDITION_FIRST = (
    #     'django.middleware.cache.UpdateCacheMiddleware',
    # )

    # MIDDLEWARE_CLASSES_ADDITION_LAST = (
    #     'django.middleware.cache.FetchFromCacheMiddleware',
    # )

    # CACHES = {
    #     'default': {
    #         'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
    #         'LOCATION': '127.0.0.1:11211',
    #     }
    # }
