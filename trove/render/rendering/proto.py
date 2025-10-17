from typing import (
    Iterator,
    Protocol,
)

__all__ = ('ProtoRendering',)


class ProtoRendering(Protocol):
    '''protocol for all renderings
    '''
    mediatype: str  # required attribute

    def iter_content(self) -> Iterator[str] | Iterator[bytes]:
        '''`iter_content`: (only) required method
        '''
