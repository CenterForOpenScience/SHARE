import logging

from share.models import ShareObject
from share.util import IDObfuscator

logger = logging.getLogger(__name__)


class SameAsMiddleware:
    def resolve(self, next, root, args, context, info):
        if isinstance(root, ShareObject) and root.same_as:
            logger.debug('Graphql request for merged object %s. Resolving to same_as object %s instead.', IDObfuscator.encode(root), IDObfuscator.encode(root.same_as))
            root = root.same_as
        return next(root, args, context, info)
