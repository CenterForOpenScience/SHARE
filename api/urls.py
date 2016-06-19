from django.conf.urls import url

from api.views import AcceptNormalizedManuscript, AcceptRawData

urlpatterns = [
    url(r'normalized/', AcceptNormalizedManuscript.as_view()),
    url(r'raw/', AcceptRawData.as_view()),
]
