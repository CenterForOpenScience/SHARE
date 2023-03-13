import dataclasses


@dataclasses.dataclass
class IndexStatus:
    specific_indexname: str
    is_current: bool = False
    is_kept_live: bool = False
    is_default_for_searching: bool = False
    creation_date: str = ''
    doc_count: int = 0
    health: str = 'nonexistent'
