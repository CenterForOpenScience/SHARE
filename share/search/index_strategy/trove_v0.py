from share.search.index_strategy._base import IndexStrategy


# just a placeholder for now
class TroveV0IndexStrategy(IndexStrategy):
    @property
    def supported_message_types(self):
        return set()

    @property
    def index_settings(self):
        raise NotImplementedError

    @property
    def index_mappings(self):
        raise NotImplementedError

    def build_action_generator(self, index_name, message_type):
        raise NotImplementedError
