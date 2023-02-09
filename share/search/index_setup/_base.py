import abc
import typing

from share.search.exceptions import IndexSetupError
from share.search import messages


class IndexSetup(abc.ABC):
    def assert_message_type(self, message_type):
        if message_type not in self.supported_message_types:
            raise IndexSetupError(f'Invalid message_type "{message_type}" (expected {self.supported_message_types})')

    @property
    @abc.abstractmethod
    def supported_message_types(self) -> typing.Iterable[messages.MessageType]:
        raise NotImplementedError

    @abc.abstractmethod
    def handle_message(self, message: messages.DaemonMessage):
        raise NotImplementedError

    @abc.abstractmethod
    def delete_index(self, index_name):
        raise NotImplementedError

    @abc.abstractmethod
    def create_index(self, index_name):
        raise NotImplementedError

    @abc.abstractmethod
    def index_exists(self, index_name):
        raise NotImplementedError

    @abc.abstractmethod
    def update_mappings(self, index_name):
        raise NotImplementedError

    @abc.abstractmethod
    def stream_actions(self, action_gen):
        raise NotImplementedError

    @abc.abstractmethod
    def send_actions_sync(self, action_gen):
        raise NotImplementedError

    @abc.abstractmethod
    def refresh_indexes(self):
        raise NotImplementedError


class Elastic5IndexSetup(IndexSetup):
    @property
    @abc.abstractmethod
    def index_settings(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def index_mappings(self):
        raise NotImplementedError

    @abc.abstractmethod
    def build_action_generator(self, index_name, message_type):
        raise NotImplementedError
