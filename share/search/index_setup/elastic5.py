import abc

from django.conf import settings
from elasticsearch5 import Elasticsearch, helpers as elastic5_helpers

from share.search.index_setup._base import IndexSetup


class Elastic5IndexSetup(IndexSetup):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        should_sniff = settings.ELASTICSEARCH['SNIFF']
        self.es5_client = Elasticsearch(
            self.cluster_url,
            retry_on_timeout=True,
            timeout=settings.ELASTICSEARCH['TIMEOUT'],
            # sniff before doing anything
            sniff_on_start=should_sniff,
            # refresh nodes after a node fails to respond
            sniff_on_connection_fail=should_sniff,
            # and also every 60 seconds
            sniffer_timeout=60 if should_sniff else None,
        )

    @abc.abstractmethod
    def index_settings(self):
        raise NotImplementedError

    @abc.abstractmethod
    def index_mappings(self):
        raise NotImplementedError

    @abc.abstractmethod
    def build_elastic_actions(self, message_type, messages_chunk):
        raise NotImplementedError

    def exists_as_expected(self):
        raise NotImplementedError

    def pls_setup_as_needed(self):
        raise NotImplementedError

    def pls_create(self):
        raise NotImplementedError

    def pls_delete(self):
        raise NotImplementedError

    def pls_organize_redo(self):
        raise NotImplementedError

    def pls_handle_messages(self, message_type, messages_chunk):
        (success_count, errors) = elastic5_helpers.bulk(
            self.es5_client,
            self.build_elastic_actions(message_type, messages_chunk),
            raise_on_error=False,
        )
        print(errors)
        import pdb; pdb.set_trace()
        for error in errors:
            # yield error response
            pass
