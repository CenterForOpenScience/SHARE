import providers.gov.scitech.normalizer as SciTechParser

from share.normalize.normalizer import Normalizer


class DoepagesNormalizer(Normalizer):

    # Use the SciTech Parser since DOE Pages follows the same schema
    root_parser = SciTechParser.CreativeWork
