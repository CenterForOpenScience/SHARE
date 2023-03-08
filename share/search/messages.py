import abc
import dataclasses
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
    BACKFILL_SUID = 'fill-suid'

    @property
    def is_backfill(self):
        return self in BACKFILL_MESSAGE_TYPES


BACKFILL_MESSAGE_TYPES = {
    MessageType.BACKFILL_SUID,
}


class IndexMessage(typing.NamedTuple):
    message_type: MessageType
    target_id: int


class IndexMessageResponse(typing.NamedTuple):
    is_handled: bool
    index_message: IndexMessage
    error_label: typing.Optional[str]


@dataclasses.dataclass
class MessagesChunk:
    message_type: MessageType
    target_ids_chunk: typing.Iterable[int]

    def as_dicts(self):
        for target_id in self.target_ids_chunk:
            yield {
                'version': 2,
                'message_type': self.message_type.value,
                'target_id': target_id,
            }

    def as_tuples(self):
        for target_id in self.target_ids_chunk:
            yield IndexMessage(
                message_type=self.message_type,
                target_id=target_id,
            )


class DaemonMessage(abc.ABC):
    PROTOCOL_VERSION = None

    @classmethod
    def from_received_message(cls, kombu_message):
        version = kombu_message.payload.get('version', 0)
        for klass in cls.__subclasses__():
            if klass.PROTOCOL_VERSION == version:
                return klass(kombu_message=kombu_message)
        raise ValueError('Invalid version "{}"'.format(version))

    @property
    @abc.abstractmethod
    def message_type(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def target_id(self):
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

    @property
    def message_type(self):
        return MessageType(self.kombu_message.payload['message_type'])

    @property
    def target_id(self):
        return self.kombu_message.payload['target_id']
