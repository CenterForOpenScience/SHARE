from django.urls import path

from . import views


urlpatterns = [
    path(
        'urn:checksumname/<str:checksum_algorithm>/<path:checksum_value>',
        views.view_checksumname,
        name='checksumname',
    ),
]
