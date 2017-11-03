from django.conf.urls import url

from api import views

app_name = 'api'

urlpatterns = [
    url(r'share/data/?', views.V1DataView.as_view(), name='v1data')
]
