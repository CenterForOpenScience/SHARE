from enum import Enum
import logging
import typing

from share.search import exceptions


logger = logging.getLogger(__name__)


class MessageType(Enum):
    INDEX_AGENT = 'Agent'
    INDEX_CREATIVEWORK = 'CreativeWork'
    INDEX_TAG = 'Tag'
    INDEX_SUBJECT = 'Subject'

    INDEX_SUID = 'suid'


class DaemonMessage:
    PROTOCOL_VERSION = None

    @classmethod
    def from_received_message(cls, kombu_message):
        version = kombu_message.payload.get('version', 0)
        for klass in cls.__subclasses__():
            if klass.PROTOCOL_VERSION == version:
                return klass(kombu_message=kombu_message)
        raise ValueError('Invalid version "{}"'.format(version))

    @classmethod
    def from_values(cls, message_type, target_ids):
        return [
            V2Message(message_type=message_type, target_id=target_id)
            for target_id in target_ids
        ]

    @property
    def message_type(self):
        raise NotImplementedError

    @property
    def target_id(self):
        raise NotImplementedError

    def to_dict(self):
        raise NotImplementedError

    def __init__(self, *, kombu_message=None):
        self.kombu_message = kombu_message

    def ack(self):
        if self.kombu_message is None:
            raise exceptions.DaemonMessageError('ack! called DaemonMessage.ack() but there is nothing to ack')
        return self.kombu_message.ack()

    def requeue(self):
        if self.kombu_message is None:
            raise exceptions.DaemonMessageError('called DaemonMessage.requeue() but there is nothing to requeue')
        return self.kombu_message.reject_log_error(logger, Exception, requeue=True)

    def __repr__(self):
        return f'<{self.__class__.__name__}({self.message_type}, {self.target_id})>'

    def __hash__(self):
        return hash((self.message_type, self.target_id))

    def __eq__(self, other):
        return (
            isinstance(other, DaemonMessage)
            and self.message_type == other.message_type
            and self.target_id == other.target_id
        )


class V2Message(DaemonMessage):
    """
    e.g.
    {
        "version": 2,
        "message_type": "suid",
        "target_id": 7,
    }
    """
    PROTOCOL_VERSION = 2

    def __init__(self, *, kombu_message=None, message_type=None, target_id=None):
        if kombu_message is None:
            assert message_type is not None
            assert target_id is not None
            super().__init__()
            # override properties
            self.message_type = message_type
            self.target_id = target_id
        else:
            assert message_type is None
            assert target_id is None
            super().__init__(kombu_message)

    @property
    def message_type(self):
        return MessageType(self.kombu_message.payload['message_type'])

    @property
    def target_id(self):
        return self.kombu_message.payload['target_id']

    def to_dict(self):
        return {
            'version': self.PROTOCOL_VERSION,
            'message_type': self.message_type.value,
            'target_id': self.target_id,
        }


class HandledMessageResponse(typing.NamedTuple):
    is_handled: bool
    daemon_message: DaemonMessage
    error_message: typing.Optional[str]
