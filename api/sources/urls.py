from rest_framework.routers import DefaultRouter

from api.sources import views


router = DefaultRouter()
router.register(r'sources', views.SourceViewSet, base_name='source')
urlpatterns = router.urls
