import argparse
import json
import sys

import jinja2
from OSMPythonTools.overpass import Overpass

from nlmaps_tools.parse_mrl import MrlGrammar, Symbol


OVERPASS_URL = 'https://overpass-api.de/api/interpreter'

ENV = jinja2.Environment(
    loader=jinja2.PackageLoader('nlmaps_tools', 'overpass_templates'),
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
)

ENV.globals['esc'] = lambda x: x

#area(3600062422)->.a;(node(area.a)["shop"="bakery"];way(area.a)["shop"="bakery"];relation(area.a)["shop"="bakery"];);out;


def has_name(tags):
    return any(key == 'name' for key, _ in tags)


def geojson(elements):
    # TODO: Handle relations correctly.
    features = []
    for elm in elements:
        if elm.type() not in ['node', 'way']:
            continue
        popup = '<b>{}</b><br>lat: {} lon: {}<br>{}'.format(
            element_name(elm), elm.lat(), elm.lon(),
            '<br>'.join('{}: {}'.format(key, val)
                        for key, val in elm.tags().items())
        )
        feature = {
            'type': 'Feature',
            'geometry': elm.geometry(),
            'properties': {
                'popupContent': popup
            }
        }
        features.append(feature)
    return {'type': 'FeatureCollection', 'features': features}


def element_name(element):
    name = element.tag('name')
    if name:
        return name
    return element.id()


def apply_qtype(qtype, elements):
    if qtype == Symbol('latlong'):
        return {'type': 'map'}
    elif qtype == ('least', ('topx', Symbol('1'))):
        text = 'Yes' if len(elements) > 0 else 'No'
        return {'type': 'text', 'text': text}
    elif qtype == Symbol('count'):
        return {'type': 'text', 'text': str(len(elements))}
    elif qtype == Symbol('count'):
        return {'type': 'text', 'text': str(len(elements))}
    elif isinstance(qtype, tuple) and qtype[0] == 'findkey':
        # TODO: Handle multiple keys
        key = qtype[1]
        name = lambda elm: elm.id() if key == 'name' else element_name(elm)
        values = ['{}: {}'.format(name(elm), str(elm.tag(key)))
                  for elm in elements]
        return {'type': 'list', 'list': values}
    return {'type': 'Error', 'error': 'Unknown qtype: {}'.format(qtype)}


def answer_in_query(features, overpass_url=OVERPASS_URL):
    overpass = Overpass()
    if 'area' in features:
        template = ENV.get_template('in_query/area.jinja2')
    elif has_name(features['target_nwr']):
        template = ENV.get_template('in_query/name.jinja2')
    else:
        ans = {'type': 'error', 'error': 'No area and no name=* tag present.'}
        return ans

    ql = template.render(features=features)
    try:
        result = overpass.query(ql)
    except:
        ans = {'type': 'error',
               'error': 'Error when retrieving result. Maybe a Timeout?'}
        return ans

    elements = result.elements()

    answers = {'type': 'sub', 'sub': [], 'geojson': geojson(elements)}
    for qtype in features['qtype']:
        answers['sub'].append(apply_qtype(qtype, elements))
    return answers


def answer(features):
    if features['query_type'] == 'in_query':
        return answer_in_query(features)
    return {
        'type': 'error',
        'error': 'query_type {} not supported yet'.format(
            features['query_type'])
    }


def load_features(mrl, escaped=False):
    if isinstance(mrl, str):
        mrl = mrl.strip()
        if mrl.startswith('dist(') or mrl.startswith('query('):
            grammar = MrlGrammar()
            try:
                parseResult = grammar.parseMrl(mrl, is_escaped=escaped)
            except:
                return None
                #print('Could not parse MRL: {}'.format(mrl), file=sys.stderr)
                #sys.exit(1)
            features = parseResult['features']

    elif isinstance(mrl, dict) and 'query_type' in mrl:
        features = mrl

    else:
        try:
            features = json.loads(mrl)
        except:
            return None
            #print('Could not load MRL features from following JSON: {}'
            #      .format(mrl), file=sys.stderr)
            #sys.exit(1)
    return features


def main(mrl, escaped=False):
    features = load_features(mrl, escaped=escaped)
    print(features)
    print(answer(features))


def parse_args():
    parser = argparse.ArgumentParser(description='Answer an MRL')
    parser.add_argument(
        'mrl',
        help='MRL as string or MRL features as json string'
    )
    parser.add_argument(
        '--escaped', action='store_true', default=False,
        help='Whether the mrl is in escaped form. Default: False'
    )
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    ARGS = parse_args()
    main(**vars(ARGS))

