from collections import OrderedDict

from django.contrib import admin
from django.core.exceptions import PermissionDenied


class SetOfEverything(list):
    def __contains__(self, other):
        return True


## adopted from http://mike.hostetlerhome.com/blog/2012/11/13/add-a-read-only-role-to-django-admin/
class ReadOnlyAdmin(admin.ModelAdmin):

    def has_add_permission(self, request, obj=None):
        return self.__user_is_readonly(request)

    def has_delete_permission(self, request, obj=None):
        return self.__user_is_readonly(request)

    def get_actions(self, request):
        # readonly users cannot perform any actions
        return OrderedDict()

    def change_view(self, request, object_id, extra_context=None):

        if self.__user_is_readonly(request):
            # every field will be readonly
            self.readonly_fields = SetOfEverything()

        try:
            return super(ReadOnlyAdmin, self).change_view(request, object_id, extra_context=extra_context)
        except PermissionDenied:
            pass
        if request.method == 'POST':
            raise PermissionDenied
        request.readonly = True
        return super(ReadOnlyAdmin, self).change_view(request, object_id, extra_context=extra_context)

    def __user_is_readonly(self, request):
        groups = [x.name for x in request.user.groups.all()]

        return 'readonly' in groups
