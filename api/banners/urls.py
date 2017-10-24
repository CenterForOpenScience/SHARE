from rest_framework.routers import SimpleRouter
from api.banners import views


router = SimpleRouter()
router.register(r'site_banners', views.SiteBannerViewSet, base_name='site_banners')
urlpatterns = router.urls
