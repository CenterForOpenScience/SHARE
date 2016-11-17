from providers.io.osf.harvester import OSFHarvester


class OSFRegistrationsHarvester(OSFHarvester):
    PATH = 'v2/registrations/'

    def build_url(self, start_date, end_date):
        url = super().build_url(start_date, end_date)
        url.args['embed'] = 'identifiers'
        return url
