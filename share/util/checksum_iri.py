from __future__ import annotations
from collections.abc import Callable
import dataclasses
import hashlib
import json
from typing import Self, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from trove.util.json import JsonValue


type HexdigestFn = Callable[[str | bytes, str | bytes], str]


def _ensure_bytes(bytes_or_something: bytes | str) -> bytes:
    if isinstance(bytes_or_something, bytes):
        return bytes_or_something
    if isinstance(bytes_or_something, str):
        return bytes_or_something.encode()
    raise NotImplementedError(f'how bytes? ({bytes_or_something})')


def _builtin_checksum(hash_constructor: Any) -> HexdigestFn:
    def hexdigest_fn(salt: str | bytes, data: str | bytes) -> str:
        hasher = hash_constructor()
        hasher.update(_ensure_bytes(salt))
        hasher.update(_ensure_bytes(data))
        return str(hasher.hexdigest())
    return hexdigest_fn


CHECKSUM_ALGORITHMS = {
    'sha-256': _builtin_checksum(hashlib.sha256),
    'sha-384': _builtin_checksum(hashlib.sha384),
    'sha-512': _builtin_checksum(hashlib.sha512),
}


@dataclasses.dataclass(frozen=True)
class ChecksumIri:
    checksumalgorithm_name: str
    salt: str
    hexdigest: str

    def __str__(self) -> str:
        return f'urn:checksum:{self.checksumalgorithm_name}:{self.salt}:{self.hexdigest}'

    @classmethod
    def digest(cls, checksumalgorithm_name: str, *, salt: str, data: str) -> Self:
        try:
            hexdigest_fn = CHECKSUM_ALGORITHMS[checksumalgorithm_name]
        except KeyError:
            raise ValueError(
                f'unknown checksum algorithm "{checksumalgorithm_name}"'
                f' (would recognize {set(CHECKSUM_ALGORITHMS.keys())})'
            )
        return cls(
            checksumalgorithm_name=checksumalgorithm_name,
            salt=salt,
            hexdigest=hexdigest_fn(salt, data),
        )

    @classmethod
    def digest_json(cls, checksumalgorithm_name: str, *, salt: str, raw_json: JsonValue) -> Self:
        return cls.digest(
            checksumalgorithm_name,
            salt=salt,
            data=json.dumps(raw_json, sort_keys=True),
        )

    @classmethod
    def from_iri(cls, checksum_iri: str) -> Self:
        try:
            (urn, checksum, algorithmname, salt, hexdigest) = checksum_iri.split(':')
            assert (urn, checksum) == ('urn', 'checksum')
            # TODO: checks on algorithmname, salt, hexdigest
        except (ValueError, AssertionError):
            raise ValueError(f'invalid checksum iri "{checksum_iri}"')
        return cls(
            checksumalgorithm_name=algorithmname,
            salt=salt,
            hexdigest=hexdigest,
        )
