from abc import ABC, abstractmethod

from share.search.exceptions import IndexSetupError


class IndexSetup(ABC):
    @property
    @abstractmethod
    def supported_message_types(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def index_settings(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def index_mappings(self):
        raise NotImplementedError

    @abstractmethod
    def build_action_generator(self, index_name, message_type):
        raise NotImplementedError

    def assert_message_type(self, message_type):
        if message_type not in self.supported_message_types:
            raise IndexSetupError(f'Invalid message_type "{message_type}" (expected {self.supported_message_types})')
