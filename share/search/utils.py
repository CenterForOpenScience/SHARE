

def handle_messages_sync(index_strategys, message_type, target_ids):
    messages_chunk = messages.DaemonMessage.from_values(message_type, target_ids)
    for index_strategy in index_strategys:
        if message_type not in index_strategy.supported_message_types:
            logger.error(f'skipping: {index_strategy.name} does not support {message_type}')
            continue
        for result in index_strategy.pls_handle_messages(message_type, messages_chunk):
            if not result.is_handled:
                logger.error(
                    'error in %s handling message %s: %s',
                    (index_strategy, result.daemon_message, result.error_message),
                )
            else:
                logger.info(
                    'success! %s handled message %s',
                    (index_strategy, result.daemon_message),
                )
