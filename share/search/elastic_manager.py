import abc
import importlib
import logging

from django.conf import settings

from share.util.extensions import Extensions


logger = logging.getLogger(__name__)


class MulticlusterElasticManager:
    MAX_CHUNK_BYTES = 10 * 1024 ** 2  # 10 megs

    def __init__(self, custom_settings=None):
        self.settings = custom_settings or settings.ELASTICSEARCH
        self._cluster_managers = {}

    def get_cluster_manager_for_index(self, index_name):
        cluster_id = self.settings['INDEXES'][index_name]['CLUSTER']
        if cluster_id not in self._cluster_managers:
            cluster_info = self.settings['CLUSTERS'][cluster_id]
            module_name, _, class_name = cluster_info['MANAGER_CLASS'].rpartition('.')
            manager_class = getattr(importlib.import_module(module_name), class_name)
            self._cluster_managers[cluster_id] = manager_class(cluster_info)
        return self._cluster_managers[cluster_id]

    def get_index_setup(self, index_name):
        index_setup_name = self.settings['INDEXES'][index_name]['INDEX_SETUP']
        return Extensions.get('share.search.index_setup', index_setup_name)()

    def delete_index(self, index_name):
        logger.warning(f'ElasticManager: deleting index {index_name}')
        self.es_client.indices.delete(index=index_name, ignore=[400, 404])

    def create_index(self, index_name):
        index_setup = self.get_index_setup(index_name)

        if self.es_client.indices.exists(index_name):
            raise ValueError(f'index already exists: {index_name}')

        logger.debug('Ensuring Elasticsearch index %s', index_name)
        self.es_client.indices.create(
            index_name,
            body={'settings': index_setup.index_settings},
        )

        logger.info('Putting Elasticsearch mappings')
        self.update_mappings(index_name)

        self.es_client.indices.refresh(index_name)

        logger.debug('Waiting for yellow status')
        self.es_client.cluster.health(wait_for_status='yellow')
        logger.info('Finished setting up Elasticsearch index %s', index_name)

    def update_mappings(self, index_name):
        index_setup = self.get_index_setup(index_name)

        for doc_type, mapping in index_setup.index_mappings.items():
            logger.debug('Putting mapping for %s', doc_type)
            self.es_client.indices.put_mapping(
                doc_type=doc_type,
                body={doc_type: mapping},
                index=index_name,
            )

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

    def get_primary_indexes(self):
        alias = settings.ELASTICSEARCH['PRIMARY_INDEX']

        try:
            aliases = self.es_client.indices.get_alias(name=alias)
            return list(aliases.keys())
        except NotFoundError:
            return []

    def update_primary_alias(self, primary_index_name):
        alias = settings.ELASTICSEARCH['PRIMARY_INDEX']

        previous_indexes = self.get_primary_indexes()

        if previous_indexes == [primary_index_name]:
            logger.warning(f'index {primary_index_name} is already the primary')
            return

        logger.warning(f'removing aliases to {previous_indexes} and adding alias to {primary_index_name}')
        delete_actions = [
            {'remove': {'index': index_name, 'alias': alias}}
            for index_name in previous_indexes
        ]
        add_action = {'add': {'index': primary_index_name, 'alias': alias}}
        self.es_client.indices.update_aliases(body={
            'actions': [
                *delete_actions,
                add_action
            ],
        })


class UniclusterElasticManager(abc.ABC):
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
