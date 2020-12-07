from share.models import Agent, CreativeWork, Tag, Subject

from share.search.exceptions import IndexSetupError
from share.search.fetchers import fetcher_for
from share.search.index_setup.base import IndexSetup
from share.search.index_setup.postrend_backcompat import PostRendBackcompatIndexSetup
from share.search.messages import MessageType


# composes PostRendBackcompatIndexSetup so we can explicitly reuse settings/mappings
# and easily delete this as soon as we don't need it
class ShareClassicIndexSetup(IndexSetup):
    def __init__(self):
        self.backcompat_setup = PostRendBackcompatIndexSetup()

    @property
    def supported_message_types(self):
        return {
            MessageType.INDEX_AGENT,
            MessageType.INDEX_CREATIVEWORK,
            MessageType.INDEX_TAG,
            MessageType.INDEX_SUBJECT,
        }

    @property
    def index_settings(self):
        return self.backcompat_setup.index_settings

    @property
    def index_mappings(self):
        return self.backcompat_setup.index_mappings

    def build_action_generator(self, index_name, message_type):
        if message_type not in self.supported_message_types:
            raise IndexSetupError(f'Invalid message_type "{message_type}" (expected {self.supported_message_types})')

        model, doc_type = self._get_model_and_doc_type(message_type)
        fetcher = fetcher_for(model)

        action_template = {
            '_index': index_name,
            '_type': doc_type
        }

        def action_generator(target_id_iter):
            for target_id, result in zip(target_id_iter, fetcher(target_id_iter)):
                if result is None:
                    action = None
                elif result.pop('is_deleted', False):
                    action = {'_id': result['id'], '_op_type': 'delete', **action_template}
                else:
                    action = {'_id': result['id'], '_op_type': 'index', **action_template, '_source': result}
                yield (target_id, action)
        return action_generator

    def _get_model_and_doc_type(self, message_type):
        return {
            MessageType.INDEX_AGENT: (Agent, 'agents'),
            MessageType.INDEX_CREATIVEWORK: (CreativeWork, 'creativeworks'),
            MessageType.INDEX_SUBJECT: (Subject, 'subjects'),
            MessageType.INDEX_TAG: (Tag, 'tags'),
        }[message_type]
