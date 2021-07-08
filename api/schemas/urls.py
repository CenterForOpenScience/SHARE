from django.urls import re_path as url

from api.schemas import views

urlpatterns = [
    url(r'^$', views.SchemaView.as_view(), name='schema'),
]
