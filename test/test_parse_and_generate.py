from nlmaps_tools.parse_mrl import MrlGrammar
from nlmaps_tools.generate_mrl import generate_from_features

from .queries import QUERIES


def test_parse_and_generate():
    grammar = MrlGrammar()
    for query in QUERIES:
        parse_result = grammar.parseMrl(query['mrl'])
        generated_mrl = generate_from_features(parse_result['features'])
        assert generated_mrl == query['mrl']
