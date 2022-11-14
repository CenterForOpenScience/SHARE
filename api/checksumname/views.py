from http import HttpStatus
import typing

from django.http import HttpResponse
from share import models as db


class ChecksumName(typing.NamedTuple):
    checksum_algorithm: str  # maybe from https://www.iana.org/assignments/hash-function-text-names
    checksum_value: str  # hexadecimal-encoded hash digest


class UnknownChecksumName(Exception):
    pass


class WrongChecksumName(Exception):
    pass


def view_checksumname(request, checksum_algorithm, checksum_value):
    checksumname = ChecksumName(checksum_algorithm, checksum_value)
    if request.method == 'HEAD':
        if not is_checksumname_known(checksumname):
            return HttpResponse(status=HttpStatus.NOT_FOUND)
        return HttpResponse(status=HttpStatus.OK)

    if request.method == 'GET':
        try:
            requested_record = get_checksumnamed_record(checksumname)
        except UnknownChecksumName:
            return HttpResponse(status=HttpStatus.NOT_FOUND)
        else:
            return HttpResponse(status=HttpStatus.OK, content=requested_record)

    # TODO
    # if request.method == 'PUT':
    #     try:
    #         put_checksumnamed_record(checksumname, request.body.decode(encoding='utf-8'))
    #     except WrongChecksumName:
    #         return HttpResponse(status=HttpStatus.UNPROCESSABLE_ENTITY)
    #     else:
    #         return HttpResponse(status=HttpStatus.CREATED)

    return HttpResponse(status=HttpStatus.METHOD_NOT_ALLOWED)


def is_checksumname_known(checksumname) -> bool:
    if checksumname.checksum_algorithm != 'sha-256':
        return False
    return (
        db.RawDatum.objects
        .filter(sha256=checksumname.checksum_value)
        .exists()
    )


def get_checksumnamed_record(checksumname) -> str:
    if checksumname.checksum_algorithm != 'sha-256':
        raise UnknownChecksumName()
    try:
        raw_datum = db.RawDatum.objects.get(
            sha256=checksumname.checksum_value,
        )
    except db.RawDatum.DoesNotExist:
        raise UnknownChecksumName()
    else:
        return raw_datum.datum


# TODO
# def put_checksumnamed_record(checksumname, record_content):
#     if checksumname.checksum_algorithm != 'sha-256':
#         raise UnknownChecksumName()
#     RawDatum.objects.create(...
