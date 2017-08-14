from rest_framework.routers import DefaultRouter

from api.sourceregistrations import views


router = DefaultRouter()
router.register(r'sourceregistrations', views.ProviderRegistrationViewSet, base_name='sourceregistration')
urlpatterns = router.urls
