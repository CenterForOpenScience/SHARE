from django.core import checks


def check_all_index_strategies_current(app_configs, **kwargs):
    from share.search import index_strategy
    from share.search.exceptions import IndexStrategyError
    errors = []
    for _index_strategy in index_strategy.all_index_strategies().values():
        try:
            _index_strategy.assert_strategy_is_current()
        except IndexStrategyError as exception:
            errors.append(
                checks.Error(
                    'IndexStrategy changed without checksum confirmation!',
                    hint=str(exception),
                    obj=_index_strategy,
                    id='share.search.E001',
                )
            )
    return errors
