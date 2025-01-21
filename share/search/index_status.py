from __future__ import annotations
import dataclasses


@dataclasses.dataclass(order=True)
class IndexStatus:
    creation_date: str
    index_subname: str
    specific_indexname: str
    doc_count: int = 0
    is_kept_live: bool = False
    is_default_for_searching: bool = False


@dataclasses.dataclass
class StrategyStatus:
    strategy_name: str
    strategy_check: str
    is_set_up: bool
    is_default_for_searching: bool
    index_statuses: list[IndexStatus]
    existing_prior_strategies: list[StrategyStatus]

    @property
    def strategy_id(self):
        return f'{self.strategy_name}__{self.strategy_check}'

    @property
    def is_kept_live(self) -> bool:
        return all(_indexstatus.is_kept_live for _indexstatus in self.index_statuses)
