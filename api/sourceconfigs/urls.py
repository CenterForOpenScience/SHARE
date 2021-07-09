from rest_framework.routers import SimpleRouter
from api.sourceconfigs import views


router = SimpleRouter()
router.register(r'sourceconfigs', views.SourceConfigViewSet, basename='sourceconfig')
urlpatterns = router.urls
