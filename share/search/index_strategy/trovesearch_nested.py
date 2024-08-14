from share.util.checksum_iri import ChecksumIri

from . import trovesearch_flattery as flattery


class TrovesearchNestedIndexStrategy(flattery.TrovesearchFlatteryIndexStrategy):
    '''a more complicated version of the "flattery" trovesearch strategy

    for `index-value-search` queries that the flatter index can't handle
    '''
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='TrovesearchNestedIndexStrategy',
        hexdigest='590b88fb82faee94188775e18c5d00300c35081bd2234b62d8434a15efca7486',
    )
