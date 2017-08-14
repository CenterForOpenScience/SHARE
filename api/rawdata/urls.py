from rest_framework.routers import DefaultRouter

from api.rawdata import views


router = DefaultRouter()
router.register(r'rawdata', views.RawDataViewSet, base_name='rawdatum')
urlpatterns = router.urls
