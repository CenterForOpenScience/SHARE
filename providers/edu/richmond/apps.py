from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
	name = 'providers.edu.richmond'
	version = '0.0.1'
	title = 'richmond'
	long_title = 'University of Richmond'
	home_page = 'http://scholarship.richmond.edu'
	url = 'http://scholarship.richmond.edu/do/oai/'