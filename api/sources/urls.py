from rest_framework.routers import SimpleRouter

from api.sources import views


router = SimpleRouter()
router.register(r'sources', views.SourceViewSet, base_name='source')
urlpatterns = router.urls
