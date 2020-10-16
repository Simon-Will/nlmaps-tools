from pyparsing import ParseException

from nlmaps_tools.parse_mrl import MrlGrammar
from nlmaps_tools.generate_mrl import generate_mrl


class Query:

    def __init__(self, features, mrl):
        self.features = features
        self.mrl = mrl

    @classmethod
    def from_mrl(cls, mrl):
        grammar = MrlGrammar()
        try:
            parseResult = grammar.parseMrl(mrl)
        except ParseException as e:
            raise ValueError('Invalid MRL') from e

        return cls(mrl=mrl, features=parseResult['features'])

    @classmethod
    def from_features(cls, features):
        mrl = generate_mrl(features)
        return cls(mrl=mrl, features=features)
