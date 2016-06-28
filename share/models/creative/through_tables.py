from share.models.base import ShareObject
from share.models.people import Identifier
from share.models.creative.meta import Institution, Venue, Funder, Award, DataProvider, Tag
from share.models.fields import ShareForeignKey

__all__ = ('ThroughInstitutions', 'ThroughVenues', 'ThroughFunders', 'ThroughAwards', 'ThroughDataProviders', 'ThroughTags', 'ThroughIdentifiers')

class ThroughInstitutions(ShareObject):
    institution = ShareForeignKey(Institution)
    creative_work = ShareForeignKey('AbstractCreativeWork')


class ThroughVenues(ShareObject):
    venue = ShareForeignKey(Venue)
    creative_work = ShareForeignKey('AbstractCreativeWork')


class ThroughFunders(ShareObject):
    funder = ShareForeignKey(Funder)
    creative_work = ShareForeignKey('AbstractCreativeWork')


class ThroughAwards(ShareObject):
    award = ShareForeignKey(Award)
    creative_work = ShareForeignKey('AbstractCreativeWork')


class ThroughDataProviders(ShareObject):
    venue = ShareForeignKey(DataProvider)
    creative_work = ShareForeignKey('AbstractCreativeWork')


class ThroughTags(ShareObject):
    tag = ShareForeignKey(Tag)
    creative_work = ShareForeignKey('AbstractCreativeWork')


class ThroughIdentifiers(ShareObject):
    identifier = ShareForeignKey(Identifier)
    person = ShareForeignKey('Person')
