from rest_framework.routers import DefaultRouter

from api.normalizeddata import views


router = DefaultRouter()
router.register(r'normalizeddata', views.NormalizedDataViewSet, base_name='normalizeddata')
urlpatterns = router.urls
