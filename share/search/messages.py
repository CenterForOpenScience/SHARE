from enum import Enum
import logging

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
    def wrap(cls, message):
        version = message.payload.get('version', 0)
        for klass in cls.__subclasses__():
            if klass.PROTOCOL_VERSION == version:
                return klass(message)
        raise ValueError('Invalid version "{}"'.format(version))

    @property
    def message_type(self):
        raise NotImplementedError

    @property
    def target_id(self):
        raise NotImplementedError

    def __init__(self, message):
        self.message = message

    def ack(self):
        return self.message.ack()

    def requeue(self):
        return self.message.reject_log_error(logger, Exception, requeue=True)

    def __repr__(self):
        return f'<{self.__class__.__name__}({self.message_type}, {self.target_id})>'


class V1Message(DaemonMessage):
    """
    {
        "version": 1,
        "model": "<model_name>",
        "ids": [id1, id2, id3...],
    }
    """
    PROTOCOL_VERSION = 1

    @property
    def message_type(self):
        return MessageType(self.message.payload['model'])

    @property
    def target_id(self):
        assert len(self.message.payload['ids']) == 1
        return self.message.payload['ids'][0]


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
        return MessageType(self.message.payload['message_type'])

    @property
    def target_id(self):
        return self.message.payload['target_id']


class V3Message(DaemonMessage):
    """
    e.g.
    {
        "version": 3,
        "@type": "https://share.osf.io/vocab/2017/MessageType/index_by_piri",
        "piri": "https://doi.org/10.foo/blah,
    }
    """
    PROTOCOL_VERSION = 3

    @property
    def message_type(self):
        return MessageType(self.message.payload['message_type'])

    @property
    def target_id(self):
        return self.message.payload['target_id']
