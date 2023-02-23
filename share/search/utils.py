import logging

from share.search import messages


logger = logging.getLogger(__name__)


def handle_messages_sync(index_strategys, messages_chunk: messages.MessagesChunk):
    for index_strategy in index_strategys:
        if messages_chunk.message_type not in index_strategy.supported_message_types:
            logger.error(f'skipping: {index_strategy.name} does not support {messages_chunk.message_type}')
            continue
        for result in index_strategy.pls_handle_messages_chunk(messages_chunk):
            if not result.is_handled:
                logger.error(
                    'error in %s handling message %s: %s',
                    (index_strategy, result.index_message, result.error_label),
                )
            else:
                logger.info(
                    'success! %s handled message %s',
                    (index_strategy, result.index_message),
                )
