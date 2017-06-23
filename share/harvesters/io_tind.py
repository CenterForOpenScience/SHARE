import logging

from furl import furl
from lxml import etree
import pendulum

from share.harvest import BaseHarvester

logger = logging.getLogger('__name__')


class TindHarvester(BaseHarvester):
    """
        Expected harvester kwargs:
            collection: collection name to harvest
            page_size: records per request
            format_code:
                'xo': MODS XML
                'xd': Dublin Core-ish XML
                'xm': MARC XML
                'hm': MARC
                'hb': HTML

        API Query Parameters:
            dt (type of date filter: 'm' for date modified)
            d1d (start of date range day)
            d1m (start of date range month)
            d1y (start of date range year)
            d2d (end of date range day)
            d2m (end of date range month)
            d2y (end of date range year)
            sc (split by collection: 0 or 1)
            sf (sort field: e.g. 'latest first')
            so (sort order: 'a' for ascending, 'd' for descending)
            rg (page size)
            jrec (offset)
            of (format code, see above)
    """
    VERSION = 1

    namespaces = {
        'mods': 'http://www.loc.gov/mods/v3',
    }

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum):
        page_size = self.kwargs['page_size']
        offset = 1
        url = furl(self.config.base_url)
        url.args.update({
            'c': self.kwargs['collection'],
            'of': self.kwargs['format_code'],
            'rg': page_size,
            'dt': 'm',
            'd1d': start_date.day,
            'd1m': start_date.month,
            'd1y': start_date.year,
            'd2d': end_date.day,
            'd2m': end_date.month,
            'd2y': end_date.year,
            'sc': 0,  # Splitting by collection screws up the page size
            'sf': 'latest first',
            'so': 'd',
        })

        while True:
            logger.debug('Making request to %s', url.url)
            resp = self.requests.get(url.url)
            resp.raise_for_status()

            parsed = etree.fromstring(resp.content, parser=etree.XMLParser(recover=True))
            records = parsed.xpath('/modsCollection/mods:mods', namespaces=self.namespaces)
            if not records:
                break

            for record in records:
                id = record.xpath('mods:recordInfo/mods:recordIdentifier', namespaces=self.namespaces)[0].text
                yield (id, etree.tostring(record, encoding=str))

            offset += page_size
            url.args['jrec'] = offset
