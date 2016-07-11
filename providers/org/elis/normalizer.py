from share.normalize.oai import OAICreativeWork

from share.normalize import tools

class ELISNormalizer(OAICreativeWork):

    # in the case of multiple languages takes the first and stores it
    list_languages = tools.Maybe(tools.Maybe(ctx.record, 'metadata')['oai_dc:dc'], 'dc:language'))
    if len(list_language) > 0:
        languages = tools.ParseLanguage(list_languages[0])
    else:
        languages = tools.ParseLanguage(list_languages)
