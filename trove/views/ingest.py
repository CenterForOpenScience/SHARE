import datetime
from http import HTTPStatus
import logging

from django import http
from django.views import View

from share.models.feature_flag import FeatureFlag
from trove import digestive_tract
from trove import exceptions as trove_exceptions
from trove.util.queryparams import parse_booly_str


logger = logging.getLogger(__name__)


class RdfIngestView(View):
    def get(self, request):
        # TODO: something? maybe show this user's most recently pushed rdf for this pid
        raise http.Http404

    def post(self, request):
        # TODO: better error responses (jsonapi? shacl:ValidationReport?)
        # TODO: permissions by focus_iri domain (compare with user's Source)?
        if not request.user.is_authenticated:
            return http.HttpResponse(status=HTTPStatus.UNAUTHORIZED)
        if FeatureFlag.objects.flag_is_up(FeatureFlag.FORBID_UNTRUSTED_FEED) and not request.user.is_trusted:
            return http.HttpResponse(status=HTTPStatus.FORBIDDEN)
        # TODO: declare/validate params with dataclass
        _focus_iri = request.GET.get('focus_iri')
        if not _focus_iri:
            return http.HttpResponse('focus_iri queryparam required', status=HTTPStatus.BAD_REQUEST)
        _record_identifier = request.GET.get('record_identifier')
        _expiration_date_str = request.GET.get('expiration_date')
        if _expiration_date_str is None:
            _expiration_date = None
        else:
            try:
                _expiration_date = datetime.date.fromisoformat(_expiration_date_str)
            except ValueError:
                return http.HttpResponse('expiration_date queryparam must be in ISO-8601 date format (YYYY-MM-DD)', status=HTTPStatus.BAD_REQUEST)
        _nonurgent = parse_booly_str(request.GET.get('nonurgent'))
        try:
            digestive_tract.ingest(
                raw_record=request.body.decode(encoding='utf-8'),
                record_mediatype=request.content_type,
                from_user=request.user,
                record_identifier=_record_identifier,
                focus_iri=_focus_iri,
                is_supplementary=(request.GET.get('is_supplementary') is not None),
                urgent=(not _nonurgent),
                expiration_date=_expiration_date,
                restore_deleted=True,
            )
        except trove_exceptions.DigestiveError as e:
            logger.exception(str(e))
            return http.HttpResponse(str(e), status=HTTPStatus.BAD_REQUEST)
        else:
            # TODO: include (link to?) extracted card(s)
            return http.HttpResponse(status=HTTPStatus.CREATED)

    def delete(self, request):
        # TODO: cleaner permissions
        if not request.user.is_authenticated:
            return http.HttpResponse(status=HTTPStatus.UNAUTHORIZED)
        if FeatureFlag.objects.flag_is_up(FeatureFlag.FORBID_UNTRUSTED_FEED) and not request.user.is_trusted:
            return http.HttpResponse(status=HTTPStatus.FORBIDDEN)
        # TODO: declare/validate params with dataclass
        _record_identifier = request.GET.get('record_identifier')
        if not _record_identifier:
            return http.HttpResponse('record_identifier queryparam required', status=HTTPStatus.BAD_REQUEST)
        digestive_tract.expel(
            from_user=request.user,
            record_identifier=_record_identifier,
        )
        return http.HttpResponse(status=HTTPStatus.OK)
