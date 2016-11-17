from providers.io.osf.harvester import OSFHarvester


class SocarxivHarvester(OSFHarvester):

    def build_url(self, start_date, end_date):
        url = super().build_url(start_date, end_date)
        url.args['filter[tags]'] = 'socarxiv'  # temporary - remove with proper preprint harvest
        return url
