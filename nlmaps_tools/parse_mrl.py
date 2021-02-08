import re

import pyparsing as pp


class Symbol:
    """This is used for handling unquoted MRL literals like latlong or
    count, and it is also used for numbers like 5000."""

    def __init__(self, string):
        self.string = string

    def __str__(self):
        return self.string

    def __repr__(self):
        return 'Symbol({!r})'.format(self.string)

    def __eq__(self, other):
        return isinstance(other, Symbol) and other.string == self.string


def escape_backslashes_and_single_quotes(mrl, _ignore_matches=tuple()):
    """Escape quoted name values in an MRL by prepending a backslash.

    A single quote inside a single-quoted name will be rendered as \\'
    A backslash inside a single-quoted name will be rendered as \\\\

    E.g., if the MRL contains "keyval('name','Rue d' Fleur')", this will be
    turned into "keyval('name','Rue d\\' Fleur')".

    This function fails for mrls containing a name with the string ') or ')) in
    it.
    """
    regex = r"keyval\( *'name', *'(.*?)'\)[,)]"
    for idx, match in enumerate(re.finditer(regex, mrl)):
        value = match.group(1)
        if idx not in _ignore_matches and ("'" in value or '\\' in value):
            start = match.span(1)[0]
            new_value = value.replace('\\', '\\\\').replace("'", "\\'")
            new_mrl = mrl[:start] + new_value + mrl[start + len(value):]

            _ignore_matches = set([idx]).union(_ignore_matches)
            return escape_backslashes_and_single_quotes(new_mrl,
                                                        _ignore_matches)
    return mrl


def make_tuples(nested_iterable):
    """Convert a nested iterable into nested tuples.

    >>> make_tuples([Symbol('latlong'), ['least', ['topx', Symbol('1')]]])
    (Symbol('latlong'), ('least', ('topx', Symbol('1'))))
    """
    if isinstance(nested_iterable, (str, Symbol)):
        return nested_iterable
    elif hasattr(nested_iterable, '__iter__'):
        return tuple(make_tuples(elm) for elm in nested_iterable)
    else:
        raise ValueError('Unexpected type: {}'.format(type(nested_iterable)))


def get_tags(*nwr_args):
    """Get a tree of tags from an MRL’s nwr arguments.

    >>> get_tags(*[pp.ParseResults(['keyval', 'amenity', 'restaurant']), pp.ParseResults(['or', ['keyval', 'shop', 'alcohol'], ['keyval', 'shop', 'wine']])])
    [('amenity', 'restaurant'), ('or', ('shop', 'alcohol'), ('shop', 'wine'))]
    """
    tags = []
    for arg in nwr_args:
        if arg[0] == 'keyval':
            if isinstance(arg[2], str):
                tags.append((arg[1], arg[2]))
            elif len(arg[2]) > 0 and arg[2][0] == 'or':
                val = ('or', *arg[2][1:])
                tags.append((arg[1], val))
            else:
                raise ValueError('Unexpected element: {}'.format(arg))
        else:
            inner_tags = get_tags(*arg[1:])
            tags.append((arg[0], *inner_tags))
    return tags


def with_parens(*expressions):
    res = pp.Suppress('(')
    for i, expression in enumerate(expressions):
        res += expression
        if i != len(expressions) - 1:
            res += pp.Suppress(',')
    res += pp.Suppress(')')
    return res


def func_call(func_name, *args, make_group=True):
    if isinstance(func_name, str):
        func_name = pp.Literal(func_name)

    term = func_name + with_parens(*args)
    if make_group:
        term = pp.Group(term)

    return term


class MrlGrammar:

    def __init__(self):
        self.build_grammar()

    def build_grammar(self):
        free_string = pp.QuotedString(quoteChar="'", escChar='\\')
        key_string = free_string
        val_string = (
            free_string
            ^ func_call('and', pp.delimitedList(free_string))
        )

        qtype_symbol = (
            pp.Keyword('latlong') ^ pp.Keyword('count')
        ).setParseAction(self.makeSymbol)

        distance_symbol = (
            pp.Keyword('DIST_INTOWN') ^ pp.Keyword('DIST_OUTTOWN')
            ^ pp.Keyword('WALKING_DIST') ^ pp.Keyword('DIST_DAYTRIP')
        ).setParseAction(self.makeSymbol)

        unit_symbol = (
            pp.Keyword('km') ^ pp.Keyword('mi')
        ).setParseAction(self.makeSymbol)


        integer = (
            pp.Word(pp.nums)
            ^ (pp.Suppress("'") + pp.Word(pp.nums) + pp.Suppress("'"))
        ).setParseAction(self.makeSymbol)

        distance_term = distance_symbol ^ integer

        topx_func = func_call('topx', integer)

        findkey_term_inner = (
            func_call('findkey', val_string)
            ^ func_call('findkey', val_string, topx_func).setParseAction(self.makeSetDeprecated('topx_in_findkey'))
        )
        findkey_term = (
            findkey_term_inner
            ^ func_call('nodup', findkey_term_inner)
        )

        qtype_func = (
            func_call('least', topx_func)
            ^ func_call('latlong', topx_func)
            ^ findkey_term
        )

        qtype_term = func_call(
            'qtype', pp.delimitedList(qtype_symbol ^ qtype_func)
        ).setParseAction(self.setQType)

        val_term = (
            func_call('or', pp.delimitedList(val_string))
            ^ val_string
        )

        keyval_term_inner = func_call('keyval', key_string, val_term)
        keyval_term = keyval_term_inner ^ (
            # and means search for both things separately
            # or means search for things having any one of the tags and making a union in the end
            func_call(
                (pp.Literal('and') ^ pp.Literal('or')),
                pp.delimitedList(keyval_term_inner)
            )
        )

        area_term = func_call(
            'area',
            keyval_term
        ).setParseAction(self.setArea)

        nwr_term = func_call(
            'nwr',
            pp.delimitedList(keyval_term)
        )

        center_term = (
            func_call('center', area_term, nwr_term)
            ^ func_call('center', nwr_term)
            ^ func_call('center', area_term).setParseAction(
                self.makeSetDeprecated('deprecated_lone_area_in_center'))
        ).setParseAction(self.setCenterNwr)

        search_term = func_call(
            'search', nwr_term
        ).setParseAction(self.setSearchNwr)

        maxdist_term = func_call(
            'maxdist', distance_term
        ).setParseAction(self.setMaxdist)

        in_query = (
            (area_term + pp.Suppress(',') + nwr_term)
            ^ nwr_term
        ).setParseAction(self.setInQueryNwr)

        around_query = pp.Group(
            pp.Literal('around') + pp.Suppress('(')
            + center_term + pp.Suppress(',')
            + search_term + pp.Suppress(',')
            + maxdist_term
            + pp.Optional(pp.Suppress(',') + topx_func).setParseAction(self.setAroundTopx)
            + pp.Suppress(')')
        ).setParseAction(self.makeSetQueryType('around_query'))

        cardinal_direction = (
            pp.Literal('east') ^ pp.Literal('north')
            ^ pp.Literal('south') ^ pp.Literal('west')
        ).setParseAction(self.setCardinalDirection)
        query_term = func_call(
            'query',
            in_query ^ around_query ^ func_call(cardinal_direction,
                                                in_query ^ around_query),
            qtype_term,
            make_group=False
        )

        for_term = func_call('for', free_string).setParseAction(self.setFor)
        unit_term = func_call('unit', unit_symbol).setParseAction(self.setUnit)

        dist_term = (
            pp.Literal('dist') + pp.Suppress('(').setParseAction(self.startSubFeatures)
            + pp.Group(query_term)
            + pp.Optional(
                pp.Suppress(',').setParseAction(self.startSubFeatures)
                + pp.Group(query_term)
            ).setParseAction(self.useMainFeatures)
            + pp.Optional(
                pp.Suppress(',')
                + pp.Group(for_term ^ unit_term)
            ) + pp.Suppress(')')
        ).setParseAction(self.makeSetQueryType('dist'))

        self.top = query_term ^ dist_term

    def setArea(self, s, loc, area):
        # area ex: [['area', ['keyval', 'name', 'Heidelberg']]]
        area_keyval = area[0][1]
        area_tag = (area_keyval[1], area_keyval[2])
        self.features['area'] = area_tag[1]

    def setAroundTopx(self, s, loc, topx):
        # topx ex: [['topx', '1']]
        if topx:
            self.features['around_topx'] = topx[0][1]

    def setCardinalDirection(self, s, loc, cardinal_direction):
        # card_dir ex: ['north']
        self.features['cardinal_direction'] = cardinal_direction[0]

    def setCenterNwr(self, s, loc, center):
        # center ex 1: [['center',
        #                ['area', ['keyval', 'name', 'Heidelberg']],
        #                ['nwr', ['keyval', 'name', 'Yorckstraße']]]]
        # center ex 2: [['center', ['area', ['keyval', 'name', 'Paris']]]]
        # center ex 3: [['center', ['nwr', ['keyval', 'name', 'Paris']]]]
        _, *center_args = center[0]
        for arg in center_args:
            if arg[0] == 'nwr':
                self.features['center_nwr'] = get_tags(*arg[1:])

    def makeSetDeprecated(self, deprecation_name):

        def setDeprecated(*args, **kwargs):
            if 'deprecations' in self.features:
                self.features['deprecations'].add(deprecation_name)
            else:
                self.features['deprecations'] = {deprecation_name}

        return setDeprecated

    def setFor(self, s, loc, for_toks):
        # for_toks ex: [['for', 'walk']]
        self.features['for'] = for_toks[0][1]

    def makeSymbol(self, s, loc, toks):
        # toks ex: ['WALKING_DIST']
        assert len(toks) == 1 and isinstance(toks[0], str)
        return [Symbol(toks[0])]

    def setMaxdist(self, s, loc, maxdist):
        # maxdist ex: [['maxdist', 'DIST_OUTTOWN']]
        dist = maxdist[0][1]
        if isinstance(dist, str) and dist.isdigit():
            dist = Symbol(dist)
        self.features['maxdist'] = dist

    def setInQueryNwr(self, s, loc, in_query):
        # in_query ex 1: [['nwr', ['keyval', 'monitoring:bicycle', 'yes']]]
        # in_query ex 2: [['area', ['keyval', 'name', 'Berlin']],
        #                 ['nwr', ['keyval',
        #                          'highway',
        #                          ['or', 'secondary', 'secondary_link']]]]
        for part in in_query:
            if part[0] == 'nwr':
                self.features['target_nwr'] = get_tags(*part[1:])

        self.makeSetQueryType('in_query')()

    def setQType(self, s, loc, qtype):
        # qtype ex 1: [['qtype', ['nodup', ['findkey', ['and', 'cuisine', 'name']]]]]
        # qtype ex 2: [['qtype', ['findkey', 'name'], 'latlong']]
        self.features['qtype'] = make_tuples(qtype[0][1:])

    def makeSetQueryType(self, query_type):

        def setQueryType(*args, **kwargs):
            self.features['query_type'] = query_type

        return setQueryType

    def setSearchNwr(self, s, loc, search):
        # search ex: [['search', ['nwr', ['keyval', 'religion', 'muslim']]]]
        nwr = search[0][1]
        self.features['target_nwr'] = get_tags(*nwr[1:])

    def setUnit(self, s, loc, unit):
        # for_toks ex: [['unit', 'km']]
        self.features['unit'] = unit[0][1]


    def startSubFeatures(self, *args, **kwargs):
        if 'sub' in self.parseResult['features']:
            self.parseResult['features']['sub'].append({})
        else:
            self.parseResult['features']['sub'] = [{}]
        self.features = self.parseResult['features']['sub'][-1]

    def useMainFeatures(self, *args, **kwargs):
        self.features = self.parseResult['features']

    def parseMrl(self, mrl, is_escaped=True):
        """Parse an MRL into its tokens and feature representation.

        :param mrl: The MRL string

        :param is_escaped: Whether singlq quotes and backslashes inside quoted
            areas in the mrl are already escaped in the incoming MRL. E.g.:
                MRL contains "keyval('name','Rue d' Fleur')" -> is_escaped=False
                MRL contains "keyval('name','Rue d\\' Fleur')" -> is_escaped=True
            If your MRL comes from an NLMaps dataset, your should probably set
            is_escaped=False.

        :return: The parse result dict containing the keys 'keys' and
            'features'.
        """
        if not is_escaped:
            mrl = escape_backslashes_and_single_quotes(mrl)

        self.parseResult = {}
        self.parseResult['features'] = self.features = {}
        tokens = self.top.parseString(mrl)
        self.parseResult['tokens'] = tokens
        return self.parseResult


def filetest():
    import sys
    grammar = MrlGrammar()
    testfile = '/media/data/Dauerhaft/Studium/Computerlinguistik/Master-Arbeit/data/nlmaps_v2.1/split_1_train_dev_test/nlmaps.v2.train.mrl'
    #testfile = '/media/data/Dauerhaft/Studium/Computerlinguistik/Master-Arbeit/data/nlmaps_v3delta/v3delta.normal/nlmaps.v3delta.train.mrl'

    mrl_to_features = {}
    max_fails = 10
    fails_so_far = 0

    with open(testfile) as f:
        for line_number, line in enumerate(f, start=1):
            if fails_so_far >= max_fails:
                sys.exit(1)

            mrl = line.strip()
            try:
                features = grammar.parseMrl(mrl, is_escaped=False)
            except pp.ParseException:
                mrl_to_features[mrl] = None
                print(line_number, mrl)
                fails_so_far += 1
                continue
            mrl_to_features[mrl] = features


def test():
    grammar = MrlGrammar()

    test_mrls = [
        "query(around(center(area(keyval('name','Dortmund')),nwr(keyval('name','Springmorgen'))),search(nwr(keyval('railway','abandoned'))),maxdist(WALKING_DIST)),qtype(latlong))",
        "query(around(center(nwr(keyval('name','Frankfurt am Main'))),search(nwr(keyval('building','hall'))),maxdist(DIST_INTOWN)),qtype(least(topx(1))))",
        "query(around(center(area(keyval('name','Lyon')),nwr(keyval('name','Rue Claude-Joseph Bonnet'))),search(nwr(keyval('amenity','doctors'))),maxdist(DIST_INTOWN),topx(1)),qtype(latlong))",
        "query(area(keyval('name','Dresden')),nwr(keyval('building','greenhouse')),qtype(latlong))",
        "query(west(area(keyval('name','Dresden')),nwr(keyval('building','greenhouse'))),qtype(latlong))",
        "query(area(keyval('name','Heidelberg')),nwr(keyval('amenity','restaurant')),qtype(nodup(findkey('cuisine'))))",
        "query(area(keyval('name','Heidelberg')),nwr(keyval('amenity','restaurant')),qtype(nodup(findkey(and('cuisine','name')))))",
        "query(area(keyval('name','Heidelberg')),nwr(keyval('amenity','car_sharing')),qtype(count))"
        "query(area(keyval('name','Dortmund')),nwr(keyval('amenity','parking')),qtype(findkey('capacity:parent')))",
        "query(area(keyval('name','Paris')),nwr(and(keyval('shop','bakery'),keyval('shop','butcher'))),qtype(latlong))",
        "query(area(keyval('name','Heidelberg')),nwr(keyval('amenity','place_of_worship'),keyval('denomination','catholic')),qtype(latlong))",
        "query(area(keyval('name','Berlin')),nwr(keyval('highway',or('secondary','secondary_link'))),qtype(count))",
        "query(nwr(keyval('monitoring:bicycle','yes')),qtype(findkey('name')))",
        "query(around(center(area(keyval('name','Heidelberg')),nwr(keyval('name','Yorckstraße'))),search(nwr(and(keyval('amenity','bank'),keyval('amenity','pharmacy')))),maxdist(DIST_INTOWN),topx(1)),qtype(latlong))",
        "query(around(center(area(keyval('name','Heidelberg')),nwr(keyval('name','INF 325'))),search(nwr(keyval('shop','supermarket'),or(keyval('organic','only'),keyval('organic','yes')))),maxdist(5000)),qtype(latlong))",
        "query(north(around(center(area(keyval('name','Paris'))),search(nwr(keyval('religion','muslim'))),maxdist(DIST_OUTTOWN))),qtype(least(topx(1))))",
        "query(area(keyval('name','Edinburgh')),nwr(keyval('amenity','fuel')),qtype(latlong,nodup(findkey('brand'))))",
        "query(area(keyval('name','Heidelberg')),nwr(keyval('amenity','restaurant'),keyval('cuisine',or('greek','italian'))),qtype(findkey('name')))",
        "query(area(keyval('name','Edinburgh')),nwr(keyval('tourism','hotel'),keyval('stars','4')),qtype(findkey('name',topx(1))))",
        "dist(query(area(keyval('name','Edinburgh')),nwr(keyval('name','Palace of Holyroodhouse')),qtype(latlong)),query(area(keyval('name','Edinburgh')),nwr(keyval('name','Camera Obscura')),qtype(latlong)))",
        "dist(query(around(center(area(keyval('name','Edinburgh')),nwr(keyval('name','Palace of Holyroodhouse'))),search(nwr(keyval('name','Edinburgh Waverley'),keyval('railway','station'))),maxdist(DIST_INTOWN)),qtype(latlong)))",
        "dist(query(area(keyval('name','Heidelberg')),nwr(keyval('name','Heidelberger Schloss')),qtype(latlong)),query(area(keyval('name','Heidelberg')),nwr(keyval('name','Heidelberg Hbf')),qtype(least(topx(1)))),for('walk'))",
        "query(nwr(keyval('amenity','restaurant')),qtype(latlong))",
        "query(around(center(area(keyval('name','Heidelberg')),nwr(keyval('name','INF 325'))),search(nwr(keyval('shop','supermarket'),or(keyval('organic','only'),keyval('organic','yes')))),maxdist('5000')),qtype(latlong))",
    ]

    for mrl in test_mrls:
        parseResult = grammar.parseMrl(mrl)
        print(mrl)
        #print(parseResult['tokens'])
        print(parseResult['features'])


if __name__ == '__main__':
    filetest()
    #test()
