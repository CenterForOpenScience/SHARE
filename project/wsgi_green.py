"""
WSGI config for share project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

from gevent import monkey
monkey.patch_all()

from psycogreen.gevent import patch_psycopg  # noqa
patch_psycopg()

from .wsgi import application  # noqa
