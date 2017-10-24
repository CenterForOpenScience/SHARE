from rest_framework.routers import SimpleRouter
from api.sourceregistrations import views


router = SimpleRouter()
router.register(r'sourceregistrations', views.ProviderRegistrationViewSet, base_name='sourceregistration')
urlpatterns = router.urls
