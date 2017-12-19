from rest_framework.routers import SimpleRouter
from api.rawdata import views


router = SimpleRouter()
router.register(r'rawdata', views.RawDataViewSet, base_name='rawdatum')
urlpatterns = router.urls
