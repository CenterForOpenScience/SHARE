from share.search.index_setup.base import IndexSetup
from share.search.index_setup.messages import MessageType


class TroveV0IndexSetup(IndexSetup):
    @property
    def supported_message_types(self):
        return {MessageType.INDEX_SUID}

    @property
    def index_settings(self):
        return {}

    @property
    def index_mappings(self):
        return {
            'metadata_record': {
                'dynamic': 'strict',
                'properties': {
                    'vocab_irl': {
                    },
                    'keyword_irl': {
                    },
                    'reference_irl': {
                    },
                    'outcome_irl': {
                    },
                }
            }
        }

    def build_action_generator(self, index_name, message_type):
        self.assert_message_type(message_type)

        action_template = {
            '_index': index_name,
            '_type': 'metadata_record',
        }

        def action_generator(target_id_iter):
            for target_id in target_id_iter:
                try:

                    nd = NormalizedData.objects.get(
                        suid_id__in=target_id_iter,
                        record_format='sharev2_elastic',  # TODO specify in config? or don't
                    )
            for record in record_qs:
                source_doc = json.loads(record.formatted_metadata)
                if source_doc.pop('is_deleted', False):
                    action = {
                        **action_template,
                        '_id': source_doc['id'],
                        '_op_type': 'delete',
                    }
                else:
                    action = {
                        **action_template,
                        '_id': source_doc['id'],
                        '_op_type': 'index',
                        '_source': source_doc,
                    }
                yield (record.suid_id, action)
        return action_generator

