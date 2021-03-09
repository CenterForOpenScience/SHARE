from abc import ABC, abstractmethod
from typing import Optional

from share.models.core import NormalizedData


class MetadataFormatter(ABC):
    @abstractmethod
    def format(self, normalized_data: NormalizedData) -> Optional[str]:
        raise NotImplementedError
