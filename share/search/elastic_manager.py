import logging

from elasticsearch import Elasticsearch, helpers as elastic_helpers

from django.conf import settings

from share.util.extensions import Extensions


logger = logging.getLogger(__name__)


class ElasticManager:
    MAX_CHUNK_BYTES = 10 * 1024 ** 2  # 10 megs

    def __init__(self, custom_settings=None):
        self.settings = custom_settings or settings.ELASTICSEARCH

        self.es_client = Elasticsearch(
            self.settings['URL'],
            retry_on_timeout=True,
            timeout=self.settings['TIMEOUT'],
            # sniff before doing anything
            sniff_on_start=self.settings['SNIFF'],
            # refresh nodes after a node fails to respond
            sniff_on_connection_fail=self.settings['SNIFF'],
            # and also every 60 seconds
            sniffer_timeout=60 if self.settings['SNIFF'] else None,
        )

    def get_index_setup(self, index_name):
        index_setup_name = self.settings['INDEXES'][index_name]['INDEX_SETUP']
        return Extensions.get('share.search.index_setup', index_setup_name)()

    def delete_index(self, index_name):
        logger.warn(f'ElasticManager: deleting index {index_name}')
        self.es_client.indices.delete(index=index_name, ignore=[400, 404])

    def create_index(self, index_name):
        index_setup = self.get_index_setup(index_name)

        logger.debug('Ensuring Elasticsearch index %s', index_name)
        self.es_client.indices.create(index_name, ignore=400)

        logger.debug('Waiting for yellow status')
        self.es_client.cluster.health(wait_for_status='yellow')

        logger.info('Putting Elasticsearch settings')
        self.es_client.indices.close(index=index_name)
        try:
            self.es_client.indices.put_settings(body=index_setup.index_settings, index=index_name)
        finally:
            self.es_client.indices.open(index=index_name)

        logger.info('Putting Elasticsearch mappings')
        for doc_type, mapping in index_setup.index_mappings.items():
            logger.debug('Putting mapping for %s', doc_type)
            self.es_client.indices.put_mapping(
                doc_type=doc_type,
                body={doc_type: mapping},
                index=index_name,
            )

        self.es_client.indices.refresh(index_name)

        logger.info('Finished setting up Elasticsearch index %s', index_name)

    def stream_actions(self, actions):
        stream = elastic_helpers.streaming_bulk(
            self.es_client,
            actions,
            max_chunk_bytes=self.MAX_CHUNK_BYTES,
            raise_on_error=False,
        )
        for (ok, response) in stream:
            op_type, response_body = next(iter(response.items()))
            yield (ok, op_type, response_body)

    def send_actions_sync(self, actions):
        elastic_helpers.bulk(self.es_client, actions)

    def refresh_indexes(self, index_names):
        self.es_client.indices.refresh(index=','.join(index_names))
