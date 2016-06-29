from furl import furl
from lxml import etree
import logging

from share import Harvester
logger = logging.getLogger(__name__)


class ArxivHarvester(Harvester):
    """
    astro-ph, cond-mat, cs, gr-qc, hep-ex, hep-lat, hep-ph, hep-th, math, math-ph,
    nlin, nucl-ex, nucl-th, physics, q-bio, q-fin, quant-ph, stat
    """
    namespaces = {
        'ns0': 'http://purl.org/rss/1.0/',
        'admin': 'http://webns.net/mvcb/',
        'taxo': 'http://purl.org/rss/1.0/modules/taxonomy/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'syn': 'http://purl.org/rss/1.0/modules/syndication/'
    }
    url_archive_names = [
        'astro-ph', 'cond-mat', 'cs', 'gr-qc', 'hep-ex', 'hep-lat', 'hep-ph',
        'hep-th', 'math', 'math-ph', 'nlin', 'nucl-ex', 'nucl-th', 'physics',
        'q-bio', 'q-fin', 'quant-ph', 'stat'
    ]
    url = 'http://export.arxiv.org/rss/'

    def do_harvest(self, start_date, end_date):
        # Arxiv does not have dates

        # Fetch records is a separate function for readability
        # Ends up returning a list of tuples with provider given id and the document itself
        # return self.fetch_records(furl(self.url).set(query_params={
        #     'search_for': '*',
        # }).url)
        return self.fetch_records(self.url)

    def fetch_records(self, url: furl) -> list:
        """
        <item rdf:about="http://arxiv.org/abs/1606.08480">
        <title>
            Privacy Knowledge Modelling for Internet of Things: A Look Back. (arXiv:1606.08480v1 [cs.CY])
        </title>
        <link>http://arxiv.org/abs/1606.08480</link>
        <description rdf:parseType="Literal">
            <p>Internet of Things (IoT) and cloud computing together give us the ability to sense,
            collect, process, and analyse data so we can use them to better understand behaviours,
            habits, preferences and life patterns of users and lead them to consume resources more
            efficiently. In such knowledge discovery activities, privacy becomes a significant
            challenge due to the extremely personal nature of the knowledge that can be derived from
            the data and the potential risks involved. Therefore, understanding the privacy expectations
            and preferences of stakeholders is an important task in the IoT domain. In this paper, we
            review how privacy knowledge has been modelled and used in the past in different domains.
            Our goal is not only to analyse, compare and consolidate past research work but also to appreciate
            their findings and discuss their applicability towards the IoT. Finally, we discuss major research
            challenges and opportunities. </p> <p>DONATE to arXiv: One hundred percent of your contribution will
            fund improvements and new initiatives to benefit arXiv's global scientific community. Please join the
            Simons Foundation and our generous member organizations and research labs in supporting arXiv.
            https://goo.gl/QIgRpr</p>
        </description>
        <dc:creator>
            <a href="http://arxiv.org/find/cs/1/au:+Perera_C/0/1/0/all/0/1">Charith Perera</a>, <a href="http://arxiv.org/find/cs/1/au:+Liu_C/0/1/0/all/0/1">Chang Liu</a>, <a href="http://arxiv.org/find/cs/1/au:+Ranjan_R/0/1/0/all/0/1">Rajiv Ranjan</a>, <a href="http://arxiv.org/find/cs/1/au:+Wang_L/0/1/0/all/0/1">Lizhe Wang</a>, <a href="http://arxiv.org/find/cs/1/au:+Zomaya_A/0/1/0/all/0/1">Albert Y. Zomaya</a>
            </dc:creator>
        </item>
        """
        archive_names_index = 0
        records = self.fetch_page(furl(url + self.url_archive_names[archive_names_index]))

        while True:
            for record in records:
                yield (
                    record.xpath('ns0:link', namespaces=self.namespaces)[0].text,
                    etree.tostring(record),
                )

            archive_names_index += 1

            if archive_names_index >= len(self.url_archive_names):
                break

            records = self.fetch_page(furl(url + self.url_archive_names[archive_names_index]))

    def fetch_page(self, url: furl) -> (list, str):
        logger.info('Making request to {}'.format(url.url))

        resp = self.requests.get(url.url)
        parsed = etree.fromstring(resp.content)

        records = parsed.xpath('//ns0:item', namespaces=self.namespaces)

        logger.info('Found {} records.'.format(len(records)))

        return records
