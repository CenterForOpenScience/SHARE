from rest_framework.routers import SimpleRouter
from api.normalizeddata import views


router = SimpleRouter()
router.register(r'normalizeddata', views.NormalizedDataViewSet, basename='normalizeddata')
urlpatterns = router.urls
