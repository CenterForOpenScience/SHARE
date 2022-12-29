import abc
import typing


class MetadataFormatter(abc.ABC):
    @abc.abstractmethod
    def format(self, normalized_datum) -> typing.Optional[str]:
        """return a string representation of the given metadata in the formatter's format
        """
        raise NotImplementedError
