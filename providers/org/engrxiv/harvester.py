from providers.io.osf.harvester import OSFHarvester


class EngrxivHarvester(OSFHarvester):

    def build_url(self, start_date, end_date):
        url = super().build_url(start_date, end_date)
        url.args['filter[tags]'] = 'engrxiv'  # temporary - remove with proper preprint harvest
        return url
