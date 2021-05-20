from share.search.index_setup.base import IndexSetup


# just a placeholder for now
class TroveV0IndexSetup(IndexSetup):
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
