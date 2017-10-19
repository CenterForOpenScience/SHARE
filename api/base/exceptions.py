from rest_framework import status
from rest_framework_json_api import serializers
from rest_framework_json_api.exceptions import exception_handler as parent_exception_handler


def exception_handler(exc, context):
    # Return 409 Conflict on any unique constraint violations
    if isinstance(exc, serializers.ValidationError):
        codes = exc.get_codes()
        conflict = False
        if isinstance(codes, list):
            conflict = 'unique' in codes
        elif isinstance(codes, dict):
            conflict = any('unique' in c for c in codes.values())

        if conflict:
            exc.status_code = status.HTTP_409_CONFLICT

    return parent_exception_handler(exc, context)

