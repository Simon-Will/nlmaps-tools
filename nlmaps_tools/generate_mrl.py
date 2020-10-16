import os

import jinja2

from nlmaps_tools.parse_mrl import Symbol


def quote(string):
    if isinstance(string, Symbol):
        return str(string)

    content = string.translate({ord("'"): "\\'", ord('\\'): '\\\\'})
    return "'{}'".format(content)


def render_nwr(nwr_features):
    parts = []
    for feat in nwr_features:
        if feat[0] in ['or', 'and'] and isinstance(feat[1], tuple):
            parts.append('{}({})'.format(feat[0], render_nwr(feat[1:])))
        elif (len(feat) == 2 and isinstance(feat[1], tuple)
              and feat[1][0] == 'or'):
            val = ','.join(quote(f) for f in feat[1][1:])
            parts.append("keyval({},or({}))".format(quote(feat[0]), val))
        elif len(feat) == 2 and all(isinstance(f, str) for f in feat):
            parts.append("keyval({},{})".format(quote(feat[0]), quote(feat[1])))
        else:
            raise ValueError('Unexpected feature part: {}'.format(feat))

    return ','.join(parts)


def open_paren_after_functor(nested_tuple):
    parts = []
    for elm in nested_tuple:
        if isinstance(elm, (str, Symbol)):
            parts.append(quote(elm))
        elif isinstance(elm, tuple):
            functor = elm[0]
            parts.append(
                '{}({})'.format(
                    functor,
                    open_paren_after_functor(elm[1:])
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


def generate_from_features(features):
    template = ENV.get_template(features['query_type'] + '.jinja2')
    return template.render(features=features)


def main():
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
    main()
