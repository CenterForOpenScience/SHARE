from rest_framework.routers import SimpleRouter
from api.suids import views


router = SimpleRouter()
router.register(r'suids', views.SuidViewSet, basename='suid')
urlpatterns = router.urls
