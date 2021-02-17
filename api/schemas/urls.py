from django.conf.urls import url

from api.schemas import views

urlpatterns = [
    url(r'^$', views.SchemaView.as_view(), name='schema'),
]
