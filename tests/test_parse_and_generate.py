from nlmaps_tools.parse_mrl import MrlGrammar
from nlmaps_tools.generate_mrl import generate_from_features

from .queries import QUERIES


def test_parse_and_generate():
    grammar = MrlGrammar()
    for query in QUERIES:
        parse_result = grammar.parseMrl(query['mrl'])
        generated_mrl = generate_from_features(parse_result['features'])
        assert generated_mrl == query['mrl']


def test_parse_and_generate_without_escape():
    grammar = MrlGrammar()
    mrl = "query(around(center(area(keyval('name','Grenoble')),nwr(keyval('name','Rue d'Agier d'Agier'))),search(nwr(keyval('shop','apparel'))),maxdist(DIST_INTOWN)),qtype(least(topx(1))))"
    parse_result = grammar.parseMrl(mrl, is_escaped=False)
    generated_mrl = generate_from_features(parse_result['features'],
                                           escape=False)
    assert generated_mrl == mrl
