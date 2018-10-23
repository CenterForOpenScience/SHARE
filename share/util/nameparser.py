from nameparser import HumanName as OriginalHumanName
from nameparser.config import Constants

# Disable stripping emoji from names
# https://nameparser.readthedocs.io/en/latest/customize.html#don-t-remove-emojis

constants = Constants()
constants.regexes.emoji = False


class HumanName(OriginalHumanName):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, constants=constants, **kwargs)
