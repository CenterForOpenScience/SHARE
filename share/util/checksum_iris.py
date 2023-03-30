import dataclasses
import hashlib
import json


def _ensure_bytes(bytes_or_something) -> bytes:
    if isinstance(bytes_or_something, bytes):
        return bytes_or_something
    if isinstance(bytes_or_something, str):
        return bytes_or_something.encode()
    raise NotImplementedError(f'how bytes? ({bytes_or_something})')


def _builtin_checksum(hash_constructor):
    def hexdigest_fn(salt, data) -> str:
        hasher = hash_constructor()
        hasher.update(_ensure_bytes(salt))
        hasher.update(_ensure_bytes(data))
        return hasher.hexdigest()
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

    def __str__(self):
        return f'urn:checksum:{self.checksumalgorithm_name}:{self.salt}:{self.hexdigest}'

    @classmethod
    def digest(cls, checksumalgorithm_name, *, salt, raw_data):
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
            hexdigest=hexdigest_fn(salt, raw_data),
        )

    @classmethod
    def digest_json(cls, checksumalgorithm_name, *, salt, raw_json):
        return cls.digest(
            checksumalgorithm_name,
            salt=salt,
            raw_data=json.dumps(raw_json, sort_keys=True),
        )

    @classmethod
    def from_iri(cls, checksum_iri: str):
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
