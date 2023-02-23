import abc
import logging

from django.conf import settings
import elasticsearch8
from elasticsearch8.helpers import streaming_bulk

from share.search.index_strategy._base import IndexStrategy
from share.search import messages
from share.util import IDObfuscator


logger = logging.getLogger(__name__)


class Elastic8IndexStrategy(IndexStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        should_sniff = settings.ELASTICSEARCH['SNIFF']
        timeout = settings.ELASTICSEARCH['TIMEOUT']
        self.es8_client = elasticsearch8.Elasticsearch(
            self.cluster_url,
            # TODO: revisit client settings
            retry_on_timeout=True,
            timeout=timeout,
            # sniffing:
            sniff_on_start=should_sniff,
            sniff_before_requests=should_sniff,
            sniff_on_node_failure=should_sniff,
            sniff_timeout=timeout,
            min_delay_between_sniffing=timeout,
        )

    @abc.abstractmethod
    def index_settings(self):
        raise NotImplementedError  # for subclasses to implement

    @abc.abstractmethod
    def index_mappings(self):
        raise NotImplementedError  # for subclasses to implement

    @abc.abstractmethod
    def build_elastic_actions(self, message_type, messages_chunk):
        raise NotImplementedError  # for subclasses to implement

    def get_doc_id(self, message_target_id):
        return message_target_id  # here so subclasses can override if needed

    def get_message_target_id(self, doc_id):
        return doc_id  # here so subclasses can override if needed

    # implements IndexStrategy.current_setup
    def current_setup(self):
        return {
            'settings': self.index_settings(),
            'mappings': self.index_mappings(),
        }

    # implements IndexStrategy.pls_make_prime
    def pls_make_prime(self):
        indexes_with_prime_alias = self._indexes_with_prime_alias()
        if indexes_with_prime_alias != {self.current_index_name}:
            indexes_with_prime_alias.discard(self.current_index_name)
            logger.warning(f'removing aliases to {indexes_with_prime_alias} and adding alias to {self.current_index_name}')
            delete_actions = [
                {'remove': {'index': index_name, 'alias': self.name}}
                for index_name in indexes_with_prime_alias
            ]
            add_action = {'add': {'index': self.current_index_name, 'alias': self.name}}
            self.es8_client.indices.update_aliases(body={
                'actions': [
                    *delete_actions,
                    add_action
                ],
            })

    def _indexes_with_prime_alias(self):
        try:
            aliases = self.es8_client.indices.get_alias(name=self.name)
            return set(aliases.keys())
        except elasticsearch8.exceptions.NotFoundError:
            return set()

    # implements IndexStrategy.pls_create
    def pls_create(self):
        logger.debug('Ensuring index %s', self.current_index_name)
        # check index exists (if not, create)
        if not self.es8_client.indices.exists(index=self.current_index_name):
            (
                self.es8_client
                .indices
                .create(
                    index=self.current_index_name,
                    settings=self.index_settings(),
                    mappings=self.index_mappings(),
                )
            )
        self.es8_client.indices.refresh(index=self.current_index_name)
        logger.debug('Waiting for yellow status')
        self.es8_client.cluster.health(wait_for_status='yellow')
        logger.info('Finished setting up Elasticsearch index %s', self.current_index_name)

    # implements IndexStrategy.pls_delete
    def pls_delete(self):
        logger.warning(f'{self.__class__.__name__}: deleting index {self.current_index_name}')
        (
            self.es8_client
            .indices
            .delete(index=self.current_index_name, ignore=[400, 404])
        )

    def pls_handle_messages(self, message_type, messages_chunk):
        messages_by_target_id = {
            message.target_id: message
            for message in messages_chunk
        }
        bulk_stream = streaming_bulk(
            self.es8_client,
            self.build_elastic_actions(message_type, messages_chunk),
            raise_on_error=False,
        )
        for (ok, response) in bulk_stream:
            op_type, response_body = next(iter(response.items()))
            message_target_id = self.get_message_target_id(response_body['_id'])
            daemon_message = messages_by_target_id[message_target_id]
            yield messages.HandledMessageResponse(
                is_handled=ok,
                daemon_message=daemon_message,
                error_message=response_body.get('_errors'),
            )
