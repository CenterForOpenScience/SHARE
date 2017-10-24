from rest_framework.routers import SimpleRouter
from api.normalizeddata import views


router = SimpleRouter()
router.register(r'normalizeddata', views.NormalizedDataViewSet, base_name='normalizeddata')
urlpatterns = router.urls
