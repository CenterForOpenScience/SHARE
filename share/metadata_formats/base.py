from abc import ABC, abstractmethod
from typing import Optional


class MetadataFormatter(ABC):
    @abstractmethod
    def format(self, normalized_data) -> Optional[str]:
        """return a string representation of the given metadata in the formatter's format
        """
        raise NotImplementedError

    def format_as_deleted(self, suid) -> Optional[str]:
        """return a string representation of a deleted suid

        if returns None, the corresponding FormattedMetadataRecord will be deleted
        if returns a string, the FMR will not be deleted -- this is for situations
            like sharev2_elastic, where an FMR with `is_deleted: true` is required
            to trigger deletion from the elasticsearch index
        """
        return None
