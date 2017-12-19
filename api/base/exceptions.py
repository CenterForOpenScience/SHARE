from rest_framework import status
from rest_framework.exceptions import APIException


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Conflict with the current state of the resource.'
    default_code = 'conflict'


class AlreadyExistsError(ConflictError):
    default_detail = 'That resource already exists.'

    def __init__(self, existing_instance, **kwargs):
        super().__init__(**kwargs)
        self.existing_instance = existing_instance
