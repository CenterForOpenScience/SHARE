import datetime

from primitive_metadata import primitive_rdf as rdf


def datetime_isoformat_z(dt: datetime.datetime | rdf.Literal | str) -> str:
    """format (or reformat) a datetime in UTC with 'Z' timezone indicator

    for complying with standards that require the 'Z', like OAI-PMH
    https://www.openarchives.org/OAI/openarchivesprotocol.html#Dates
    """
    if isinstance(dt, rdf.Literal):
        dt = dt.unicode_value
    if isinstance(dt, str):
        dt = datetime.datetime.fromisoformat(dt)
    if isinstance(dt, datetime.datetime) and dt.tzinfo is None:
        dt = dt.astimezone(datetime.UTC)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
