from rest_framework.routers import SimpleRouter
from api.sourceconfigs import views


router = SimpleRouter()
router.register(r'sourceconfigs', views.SourceConfigViewSet, base_name='sourceconfig')
urlpatterns = router.urls
