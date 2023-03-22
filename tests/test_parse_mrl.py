import pytest

from nlmaps_tools.parse_mrl import (escape_backslashes_and_single_quotes,
                                     get_tags, make_tuples, MrlGrammar)

from .queries import QUERIES


def test_escape_backslashes_and_single_quotes():
    for query in QUERIES:
        # These mrls should not contain any backslashes or single quotes
        mrl = query['mrl']
        assert escape_backslashes_and_single_quotes(mrl) == mrl

    mrl = "query(around(center(area(keyval('name','Grenoble')),nwr(keyval('name','Rue d'Agier'))),search(nwr(keyval('shop','apparel'))),maxdist(DIST_INTOWN)),qtype(least(topx(1))))"
    new_mrl = "query(around(center(area(keyval('name','Grenoble')),nwr(keyval('name','Rue d\\'Agier'))),search(nwr(keyval('shop','apparel'))),maxdist(DIST_INTOWN)),qtype(least(topx(1))))"
    assert escape_backslashes_and_single_quotes(mrl) == new_mrl

    mrl = "query(around(center(area(keyval('name','Grenoble')),nwr(keyval('name','Rue d'Agier d'Agier'))),search(nwr(keyval('shop','apparel'))),maxdist(DIST_INTOWN)),qtype(least(topx(1))))"
    new_mrl = "query(around(center(area(keyval('name','Grenoble')),nwr(keyval('name','Rue d\\'Agier d\\'Agier'))),search(nwr(keyval('shop','apparel'))),maxdist(DIST_INTOWN)),qtype(least(topx(1))))"
    assert escape_backslashes_and_single_quotes(mrl) == new_mrl

    mrl = "query(around(center(area(keyval('name','Gr\\en\\'oble')),nwr(keyval('name','Rue d'Agier'))),search(nwr(keyval('shop','apparel'))),maxdist(DIST_INTOWN)),qtype(least(topx(1))))"
    new_mrl = "query(around(center(area(keyval('name','Gr\\\\en\\\\\\'oble')),nwr(keyval('name','Rue d\\'Agier'))),search(nwr(keyval('shop','apparel'))),maxdist(DIST_INTOWN)),qtype(least(topx(1))))"
    assert escape_backslashes_and_single_quotes(mrl) == new_mrl


def test_make_tuples():
    assert make_tuples(['latlong']) == ('latlong',)
    assert make_tuples([['least', ['topx', '1']]]) == (('least', ('topx', '1')),)
    assert make_tuples(
        ['latlong', ['nodup', ['findkey', ['and', 'cuisine', 'name']]]]
    ) == ('latlong', ('nodup', ('findkey', ('and', 'cuisine', 'name'))))
    assert make_tuples('latlong') == 'latlong'

    with pytest.raises(ValueError):
        make_tuples(1)


def test_get_tags():
    assert get_tags(
        ['keyval', 'name', 'Springmorgen']
    ) == [('name', 'Springmorgen')]

    assert get_tags(
        ['keyval', 'name', 'Springmorgen'],
        ['keyval', 'name', 'Rue Claude-Joseph Bonnet']
    ) == [('name', 'Springmorgen'), ('name', 'Rue Claude-Joseph Bonnet')]

    assert get_tags(
        ['and', ['keyval', 'shop', 'bakery'], ['keyval', 'shop', 'butcher']],
        ['keyval', 'name', 'Tauberschmidt'],
    ) == [('and', ('shop', 'bakery'), ('shop', 'butcher')),
          ('name', 'Tauberschmidt')]

    assert get_tags(
        ['keyval', 'shop', 'supermarket'],
        ['or', ['keyval', 'organic', 'only'], ['keyval', 'organic', 'yes']],
    ) == [('shop', 'supermarket'),
          ('or', ('organic', 'only'), ('organic', 'yes'))]

    assert get_tags(
        ['keyval', 'shop', ['or', 'bakery', 'butcher', 'supermarket']],
    ) == [('shop', ('or', 'bakery', 'butcher', 'supermarket'))]


def test_parse_into_features():
    grammar = MrlGrammar()
    for query in QUERIES:
        parse_result = grammar.parseMrl(query['mrl'])
        assert parse_result['features'] == query['features']
