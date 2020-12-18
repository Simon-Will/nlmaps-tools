import os

import jinja2

from nlmaps_tools.parse_mrl import Symbol


def quote(s, escape=True):
    if isinstance(s, Symbol):
        return str(s)

    if escape:
        s = s.translate({ord("'"): "\\'", ord('\\'): '\\\\'})
    return "'{}'".format(s)


def render_nwr(nwr_features, escape=True):
    parts = []
    for feat in nwr_features:
        if feat[0] in ['or', 'and'] and isinstance(feat[1], (list, tuple)):
            parts.append('{}({})'.format(feat[0], render_nwr(feat[1:], escape)))
        elif (len(feat) == 2 and isinstance(feat[1], (list, tuple))
              and feat[1][0] == 'or'):
            val = ','.join(quote(f, escape) for f in feat[1][1:])
            parts.append("keyval({},or({}))".format(quote(feat[0], escape), val))
        elif len(feat) == 2 and all(isinstance(f, str) for f in feat):
            parts.append("keyval({},{})".format(quote(feat[0], escape),
                                                quote(feat[1], escape)))
        else:
            raise ValueError('Unexpected feature part: {}'.format(feat))

    return ','.join(parts)


def open_paren_after_functor(nested_tuple, escape=True):
    parts = []
    for elm in nested_tuple:
        if isinstance(elm, (str, Symbol)):
            parts.append(quote(elm, escape))
        elif isinstance(elm, (list, tuple)):
            functor = elm[0]
            parts.append(
                '{}({})'.format(
                    functor,
                    open_paren_after_functor(elm[1:], escape)
                )
            )
        else:
            raise ValueError('Unexpected element: {}'.format(elm))

    return ','.join(parts)


ENV = jinja2.Environment(
    loader=jinja2.PackageLoader('nlmaps_tools', 'mrl_templates'),
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
)

ENV.globals['render_nwr'] = render_nwr
ENV.globals['open_paren_after_functor'] = open_paren_after_functor
ENV.globals['quote'] = quote


def generate_from_features(features, escape=True):
    """Generate an MRL from its features.

    :param features: A dict of features like those obtained by parsing with
        nlmaps_tools.parse_mrl.MrlGrammar.parseMrl
    :param escape: Whether to escape single quotes and backslashes inside
        quoted values
    :return: The generated MRL

    >>> generate_from_features({'tags': [('name', 'Heidelberg')], 'area': 'Heidelberg', 'target_nwr': [('amenity', 'restaurant')], 'query_type': 'in_query', 'qtype': (Symbol('latlong'), ('nodup', ('findkey', 'cuisine')))})
    "query(area(keyval('name','Heidelberg')),nwr(keyval('amenity','restaurant')),qtype(latlong,nodup(findkey('cuisine'))))"

    """
    template = ENV.get_template(features['query_type'] + '.jinja2')
    return template.render(features=features, escape=escape)


def test():
    features = {
        'tags': [('name', 'Heidelberg')],
        'area': 'Heidelberg',
        'target_nwr': [('amenity', 'restaurant')],
        'query_type': 'in_query',
        'qtype': (Symbol('latlong'), ('nodup', ('findkey', 'cuisine')))
    }
    print(generate_from_features(features))

    features = {
        'sub': [
            {'area': 'Edinburgh', 'target_nwr': [('name', 'Palace of Holyroodhouse')], 'query_type': 'in_query', 'qtype': (Symbol('latlong'),)},
            {'area': 'Edinburgh', 'target_nwr': [('name', 'Camera Obscura')], 'query_type': 'in_query', 'qtype': (Symbol('latlong'),)}
        ],
        'query_type': 'dist',
        'unit': Symbol('km')
    }
    print(generate_from_features(features))


if __name__ == '__main__':
    test()
