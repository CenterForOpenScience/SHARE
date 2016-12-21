from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.fr.archives-ouvertes.hal'
    version = '0.0.1'
    title = 'HAL'
    long_title = 'Hyper Articles en Ligne (HAL)'
    home_page = 'https://hal.archives-ouvertes.fr/'
    url = 'https://api.archives-ouvertes.fr/oai/hal/'
    time_granularity = False
    emitted_type = 'publication'
    type_map = {
	'info:eu-repo/semantics/article' : 'article',
	'info:eu-repo/semantics/bachelorThesis' : 'thesis',
	'info:eu-repo/semantics/masterThesis' : 'thesis',
	'info:eu-repo/semantics/doctoralThesis' : 'thesis',
	'info:eu-repo/semantics/book' : 'book',
	'info:eu-repo/semantics/bookPart' : 'book',
	'info:eu-repo/semantics/conferenceObject' : 'conferencepaper',
	'info:eu-repo/semantics/conferencePaper' : 'conferencepaper',
	'info:eu-repo/semantics/conferencePoster' : 'poster',
	'info:eu-repo/semantics/conferenceProceedings' : 'conferencepaper',
	'info:eu-repo/semantics/conferenceContribution' : 'conferencepaper',
	'info:eu-repo/semantics/ConferenceItem' : 'conferencepaper',
	'info:eu-repo/semantics/ConferencePaper' : 'conferencepaper',
	'info:eu-repo/semantics/ConferencePoster' : 'poster',
	'info:eu-repo/semantics/lecture' : 'presentation',
	'info:eu-repo/semantics/workingPaper' : 'workingpaper',
	'info:eu-repo/semantics/preprint' : 'preprint',
	'info:eu-repo/semantics/report' : 'report',
	'info:eu-repo/semantics/reportPart' : 'report',
	'info:eu-repo/semantics/contributionToPeriodical' : 'article',
	'info:eu-repo/semantics/patent' : 'patent',
	'info:eu-repo/semantics/studentThesis' : 'thesis',
    }

