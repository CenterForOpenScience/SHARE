from django import http
from django.conf import settings
from django.urls import reverse


class HttpSmartResponseRedirect(http.HttpResponseRedirect):
    status_code = 307


class HttpSmartResponsePermanentRedirect(http.HttpResponsePermanentRedirect):
    status_code = 308


def absolute_reverse(view_name, *args, **kwargs):
    return '{}{}'.format(settings.SHARE_API_URL.rstrip('/'), reverse(view_name, *args, **kwargs))
