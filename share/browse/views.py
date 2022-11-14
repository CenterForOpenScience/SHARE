from django.views.generic.base import TemplateView


class BrowseView(TemplateView):
    template_name = 'browse/browse.html'
