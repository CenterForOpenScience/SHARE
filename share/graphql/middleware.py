import logging

from share.models import ShareObject

logger = logging.getLogger(__name__)


class SameAsMiddleware:
    def resolve(self, next, root, args, context, info):
        if isinstance(root, ShareObject) and root.same_as_id:
            root = root._meta.concrete_model.objects.get_canonical(root.id)
        return next(root, args, context, info)
