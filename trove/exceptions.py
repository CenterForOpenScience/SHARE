class TroveError(Exception):
    pass


class DigestiveError(TroveError):
    pass


class ParsingError(TroveError):
    pass


class InvalidIri(ParsingError):
    pass


class InvalidQuotedIri(ParsingError):
    pass


class InvalidQueryParamName(ParsingError):
    pass
