from django.urls import path

from . import views


urlpatterns = [
    path('pls-render-metadata', views.pls_render_metadata),
]
