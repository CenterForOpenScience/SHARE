from rest_framework.routers import SimpleRouter
from api.banners import views


router = SimpleRouter()
router.register(r'^site_?banners', views.SiteBannerViewSet, basename='site_banners')
urlpatterns = router.urls
