from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.gov.nodc'
    version = '0.0.1'
    title = 'nodc'
    long_title = 'National Oceanographic Data Center'
    home_page = 'https://www.nodc.noaa.gov/'
    url = 'https://data.nodc.noaa.gov/cgi-bin/oai-pmh?verb=ListRecords&metadataPrefix=oai_dc'
