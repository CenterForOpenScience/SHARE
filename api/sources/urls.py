from rest_framework.routers import SimpleRouter
from api.sources import views


router = SimpleRouter()
router.register(r'sources', views.SourceViewSet, basename='source')
urlpatterns = router.urls
