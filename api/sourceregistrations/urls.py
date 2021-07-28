from rest_framework.routers import SimpleRouter
from api.sourceregistrations import views


router = SimpleRouter()
router.register(r'sourceregistrations', views.ProviderRegistrationViewSet, basename='sourceregistration')
urlpatterns = router.urls
