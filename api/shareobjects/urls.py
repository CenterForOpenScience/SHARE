from rest_framework.routers import SimpleRouter

from api.shareobjects.generator import EndpointGenerator


# generate share object routes
router = SimpleRouter()
EndpointGenerator(router)
urlpatterns = router.urls
