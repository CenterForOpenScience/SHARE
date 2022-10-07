from share.legacy_normalize.transform.chain import exceptions
from share.legacy_normalize.transform.chain import ctx, ChainTransformer
from share.legacy_normalize.transform.chain.links import Delegate, Map, Maybe, Try, ParseDate
from share.legacy_normalize.transform.chain.parsers import Parser

from . import io_osf as osf


class WorkIdentifier(Parser):
    uri = ctx


class Registration(osf.Project):
    date_published = ParseDate(ctx.attributes.date_registered)
    free_to_read_date = Try(ParseDate(ctx.attributes.embargo_end_date), exceptions=(exceptions.InvalidDate, ))
    identifiers = Map(Delegate(WorkIdentifier), ctx.links.html, ctx.links.self)

    class Extra:
        registration_schema = Maybe(ctx.relationships, 'registration_schema').links.related.href
        pending_registration_approval = Maybe(ctx.relationships, 'pending_registration_approval')
        registration_supplement = Maybe(ctx.attributes, 'registration_supplement')
        registered_meta_summary = Try(ctx.registered_meta.summary.value)
        withdrawn = Maybe(ctx.attributes, 'withdrawn')
        date_registered = Maybe(ctx.attributes, 'withdrawn')
        pending_embargo_approval = Maybe(ctx.attributes, 'pending_embargo_approval')
        withdrawal_justification = Maybe(ctx.attributes, 'withdrawal_justification')
        pending_withdrawal = Maybe(ctx.attributes, 'pending_withdrawal')


class OSFRegistrationsTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Registration
