from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from api import views

router = DefaultRouter()


urlpatterns = [
    url(r'share/data/?', views.V1DataView.as_view(), name='v1data')
] + router.urls
