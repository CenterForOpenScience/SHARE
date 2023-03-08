from django.core import checks


def check_all_index_strategies_current(app_configs, **kwargs):
    from share.search import IndexStrategy
    from share.search.exceptions import IndexStrategyError
    errors = []
    for index_strategy in IndexStrategy.all_strategies().values():
        try:
            index_strategy.assert_setup_is_current()
        except IndexStrategyError as error:
            errors.append(
                checks.Error(
                    'IndexStrategy setup changed without checksum confirmation!',
                    hint=str(error),
                    obj=index_strategy,
                    id='share.search.E001',
                )
            )
    return errors
