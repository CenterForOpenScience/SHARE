import abc
import typing

from share.models import NormalizedData


class MetadataFormatter(abc.ABC):
    @abc.abstractmethod
    def format(self, normalized_data: typing.Iterable[NormalizedData]) -> typing.Optional[str]:
        """return a string representation of the given metadata in the formatter's format
        """
        raise NotImplementedError
