from django.core import checks


def check_all_index_strategies_current(app_configs, **kwargs):
    from share.search import IndexStrategy
    from share.search.exceptions import IndexStrategyError
    errors = []
    for index_strategy in IndexStrategy.all_strategies():
        try:
            index_strategy.assert_strategy_is_current()
        except IndexStrategyError as exception:
            errors.append(
                checks.Error(
                    'IndexStrategy changed without checksum confirmation!',
                    hint=str(exception),
                    obj=index_strategy,
                    id='share.search.E001',
                )
            )
    return errors
