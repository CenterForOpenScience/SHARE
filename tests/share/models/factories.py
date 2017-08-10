import factory

from share import models

from tests.factories.core import *  # noqa
from tests.factories.changes import *  # noqa
from tests.factories.share_objects import *  # noqa
from tests.factories.share_objects import ShareObjectFactory


AgentFactory = AbstractAgentFactory


class PreprintFactory(AbstractCreativeWorkFactory):
    type = 'share.preprint'


class ThroughAgentWorkRelationFactory(ShareObjectFactory):
    subject = factory.SubFactory(AgentWorkRelationFactory)
    related = factory.SubFactory(AgentWorkRelationFactory)

    class Meta:
        model = models.ThroughContributor
