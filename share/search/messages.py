import abc
import dataclasses
import enum
import logging
import typing

from share.search import exceptions
from share.util import chunked


logger = logging.getLogger(__name__)


class MessageType(enum.Enum):
    # for suid-focused records:
    INDEX_SUID = 'suid'
    BACKFILL_SUID = 'backfill-suid'
    # for indexcard-based indexes:
    UPDATE_INDEXCARD = 'update-indexcard'
    BACKFILL_INDEXCARD = 'backfill-indexcard'

    @classmethod
    def from_int(cls, message_type_int: int):
        return cls[IntMessageType(message_type_int).name]

    def __int__(self):  # allows casting to integer with `int(message_type)`
        return int(IntMessageType[self.name])

    @property
    def is_backfill(self):
        return self in BACKFILL_MESSAGE_TYPES


class IntMessageType(enum.IntEnum):
    '''for mapping MessageType to int and back again
    '''
    INDEX_SUID = 5
    BACKFILL_SUID = 6
    UPDATE_INDEXCARD = 7
    BACKFILL_INDEXCARD = 8


if __debug__:
    def _enum_keys(an_enum_class):
        return frozenset(an_enum_class.__members__.keys())

    # require that IntMessageType has the same keys MessageType has
    assert _enum_keys(MessageType) == _enum_keys(IntMessageType)


BACKFILL_MESSAGE_TYPES = {
    MessageType.BACKFILL_SUID,
    MessageType.BACKFILL_INDEXCARD,
}


class IndexMessage(typing.NamedTuple):
    message_type: MessageType
    target_id: int


class IndexMessageResponse(typing.NamedTuple):
    is_done: bool
    index_message: IndexMessage
    status_code: int
    error_text: typing.Optional[str] = None


@dataclasses.dataclass
class MessagesChunk:
    message_type: MessageType
    target_ids_chunk: typing.Iterable[int]

    def as_dicts(self):
        int_message_type = int(self.message_type)
        for target_id in self.target_ids_chunk:
            yield DaemonMessage.compose_however(int_message_type, target_id)

    def as_tuples(self):
        for target_id in self.target_ids_chunk:
            yield IndexMessage(
                message_type=self.message_type,
                target_id=target_id,
            )

    @classmethod
    def stream_chunks(
        cls,
        message_type: MessageType,
        id_stream: typing.Iterable[int],
        chunk_size: int,
    ) -> 'typing.Iterable[MessagesChunk]':
        for id_chunk in chunked(id_stream, chunk_size):
            yield cls(message_type, id_chunk)


class DaemonMessage(abc.ABC):
    PROTOCOL_VERSION = None

    @staticmethod
    def compose_however(message_type: typing.Union[int, MessageType], target_id: int) -> dict:
        '''pass-thru to PreferedDaemonMessageSubclass.compose
        '''
        assert isinstance(target_id, int)
        return V3Message.compose(message_type, target_id)

    @classmethod
    def from_received_message(cls, kombu_message):
        try:
            version = kombu_message.payload['v']
        except KeyError:
            version = kombu_message.payload.get('version', 0)
        for message_class in cls.__subclasses__():
            if message_class.PROTOCOL_VERSION == version:
                return message_class(kombu_message=kombu_message)
        raise ValueError('Invalid version "{}"'.format(version))

    @classmethod
    @abc.abstractmethod
    def compose(cls, message_type: MessageType, target_id: int) -> dict:
        raise NotImplementedError

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

    @classmethod
    def compose(cls, message_type: MessageType, target_id: int) -> dict:
        return {
            'version': 2,
            'message_type': message_type.name,
            'target_id': target_id,
        }

    @property
    def message_type(self):
        return MessageType(self.kombu_message.payload['message_type'])

    @property
    def target_id(self):
        return self.kombu_message.payload['target_id']


class V3Message(DaemonMessage):
    """
    the message is a two-ple of integers (int_message_type, target_id)
    -- minimalist, for there may be many
    {
        "v": 3,
        "m": [2, 7],
    }
    """
    PROTOCOL_VERSION = 3

    @classmethod
    def compose(cls, message_type: MessageType, target_id: int) -> dict:
        if not isinstance(target_id, int):
            raise ValueError(target_id)
        return {
            'v': 3,
            'm': (int(message_type), target_id),
        }

    @property
    def _message_twople(self) -> (int, int):
        return self.kombu_message.payload['m']

    @property
    def message_type(self) -> MessageType:
        _msg_type_int, _ = self._message_twople
        return MessageType.from_int(_msg_type_int)

    @property
    def target_id(self) -> int:
        _, target_id = self._message_twople
        if not isinstance(target_id, int):
            raise ValueError(self.kombu_message.payload)
        return target_id
