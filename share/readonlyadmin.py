from django.contrib import admin
from django.core.exceptions import PermissionDenied


## adopted from http://mike.hostetlerhome.com/blog/2012/11/13/add-a-read-only-role-to-django-admin/
class ReadOnlyAdmin(admin.ModelAdmin):

    def has_add_permission(self, request, obj=None):
        return self.__user_is_readonly(request)

    def has_delete_permission(self, request, obj=None):
        return self.__user_is_readonly(request)

    def get_actions(self, request):

        actions = super(ReadOnlyAdmin, self).get_actions(request)

        if self.__user_is_readonly(request):
            if 'delete_selected' in actions:
                del actions['delete_selected']

        return actions

    def change_view(self, request, object_id, extra_context=None):

        if self.__user_is_readonly(request):
            self.readonly_fields = self.user_readonly
            self.inlines = self.user_readonly_inlines

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
