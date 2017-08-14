from rest_framework.routers import DefaultRouter

from api.banners import views


router = DefaultRouter()
router.register(r'site_banners', views.SiteBannerViewSet, base_name='site_banners')
urlpatterns = router.urls
