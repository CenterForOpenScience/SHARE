from furl import furl
import pendulum

from share.provider import OAIHarvester


class PMCHarvester(OAIHarvester):
    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum) -> list:
        url = furl(self.url)
        url.args['verb'] = 'ListRecords'
        url.args['metadataPrefix'] = 'pmc_fm'

        if self.time_granularity:
            url.args['from'] = start_date.format('YYYY-MM-DDT00:00:00', formatter='alternative') + 'Z'
            url.args['until'] = end_date.format('YYYY-MM-DDT00:00:00', formatter='alternative') + 'Z'
        else:
            url.args['from'] = start_date.date().isoformat()
            url.args['until'] = end_date.date().isoformat()

        return self.fetch_records(url)
