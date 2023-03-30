import dataclasses


@dataclasses.dataclass(order=True)
class IndexStatus:
    creation_date: str
    index_strategy_name: str
    specific_indexname: str
    is_kept_live: bool = False
    is_default_for_searching: bool = False
    doc_count: int = 0
    health: str = 'nonexistent'
