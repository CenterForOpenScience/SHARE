from django.conf.urls import url

from api.views import AcceptNormalizedManuscript

urlpatterns = [
    url(r'wut/', AcceptNormalizedManuscript.as_view()),
]
