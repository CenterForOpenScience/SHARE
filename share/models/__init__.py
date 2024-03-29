# NOTE: The order of these imports actually matter
from share.models.source_unique_identifier import SourceUniqueIdentifier
from share.models.index_backfill import IndexBackfill
from share.models.feature_flag import FeatureFlag
from share.models.core import ShareUser, NormalizedData, FormattedMetadataRecord
from share.models.ingest import *  # noqa
from share.models.registration import *  # noqa
from share.models.banner import *  # noqa
from share.models.jobs import *  # noqa
from share.models.sources import *  # noqa
from share.models.celery import *  # noqa

# TODO: replace all the `import *  # noqa` above with explicit imports and a full __all__

__all__ = (
    'ShareUser',
    'NormalizedData',
    'FormattedMetadataRecord',
    'SourceUniqueIdentifier',
    'IndexBackfill',
    'FeatureFlag',
    # ...
)
