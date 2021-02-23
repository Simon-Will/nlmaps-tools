import argparse
from collections import defaultdict
import itertools
import json
import logging
import math
import sys
import traceback

from geopy.distance import geodesic
import jinja2
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import Overpass

from nlmaps_tools.parse_mrl import MrlGrammar, Symbol

OVERPASS_URL = 'https://overpass-api.de/api/'
#OVERPASS_URL = 'https://overpass.openstreetmap.ru/api/'

USER_AGENT = 'NLMaps Web (https://nlmaps.gorgor.de/)'
NOMINATIM = Nominatim(userAgent=USER_AGENT, waitBetweenQueries=1)
OVERPASS = Overpass(endpoint=OVERPASS_URL, userAgent=USER_AGENT)

DISTS = {
    'WALKING_DIST': '1000',
    'DIST_INTOWN': '5000',
    'DIST_OUTTOWN': '20000',
    'DIST_DAYTRIP': '80000',
}

ENV = jinja2.Environment(
    loader=jinja2.PackageLoader('nlmaps_tools', 'overpass_templates'),
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
)

ENV.filters['esc'] = lambda s: s.translate({ord("'"): "\\'",
                                            ord('\\'): '\\\\'})
ENV.filters['dist_lookup'] = lambda dist: DISTS.get(str(dist), str(dist))


class AnsweringError(Exception):

    def as_response_dict(self):
        error = self.args[0] if len(self.args) > 0 else 'Unknown Error'
        return {'type': 'error', 'error': error}


# This does not properly deal with nested ors.
def canonicalize_nwr_features(nwr_features):
    parts = []
    for feat in nwr_features:
        if feat[0] in ['or', 'and'] and isinstance(feat[1], (list, tuple)):
            parts.append((feat[0], *canonicalize_nwr_features(feat[1:])))
        elif (len(feat) == 2 and isinstance(feat[1], (list, tuple))
              and feat[1][0] == 'or'):
            or_part = ['or']
            for val in feat[1][1:]:
                or_part.append((feat[0], val))
            parts.append(tuple(or_part))
        elif len(feat) == 2 and all(isinstance(f, str) for f in feat):
            parts.append((feat[0], feat[1]))
        else:
            raise ValueError('Unexpected feature part: {}'.format(feat))

    return tuple(parts)


def add_name_tags(nwr_features,
                    name_keys=('int_name', 'alt_name', 'name:en')):
    parts = []
    for feat in nwr_features:
        if feat[0] in ['or', 'and'] and isinstance(feat[1], (list, tuple)):
            parts.append((feat[0], *add_name_tags(feat[1:])))
        elif (len(feat) == 2 and isinstance(feat[1], (list, tuple))
              and feat[1][0] == 'or'):
            or_part = ['or']
            for val in feat[1][1:]:
                or_part.append((feat[0], val))
                if feat[0] == 'name':
                    for name_key in name_keys:
                        or_part.append((name_key, val))
            parts.append(tuple(or_part))
        elif len(feat) == 2 and all(isinstance(f, str) for f in feat):
            if feat[0] == 'name':
                or_part = ['or']
                or_part.append((feat[0], feat[1]))
                if feat[0] == 'name':
                    for name_key in name_keys:
                        or_part.append((name_key, feat[1]))
                parts.append(tuple(or_part))
            else:
                parts.append((feat[0], feat[1]))
        else:
            raise ValueError('Unexpected feature part: {}'.format(feat))

    return tuple(parts)


def transform_features(query_features, transform_nwr_features):
    if 'sub' in query_features:
        for i in range(len(query_features['sub'])):
            query_features['sub'][i] = transform_features(
                query_features['sub'][i], transform_nwr_features)
    else:
        query_features['target_nwr'] = transform_nwr_features(
            query_features['target_nwr'])
        if 'center_nwr' in query_features:
            query_features['center_nwr'] = transform_nwr_features(
                query_features['center_nwr'])
    return query_features


def has_name(tags):
    return any(key == 'name' for key, _ in tags)


def latlong(element):
    # TODO: Handle relations correctly.
    if element.type() == 'node':
        return element.lat(), element.lon()
    elif element.type() in ['way', 'relation']:
        if 'center' in element._json:
            center = element._json['center']
            return center['lat'], center['lon']
        if 'bounds' in element._json:
            bounds = element._json['bounds']
            # TODO: Check if this is universally correct.
            lat = bounds['minlat'] + 0.5 * (bounds['maxlat'] - bounds['minlat'])
            lon = bounds['minlon'] + 0.5 * (bounds['maxlon'] - bounds['minlon'])
            return (lat, lon)
    return None


def geojson(elements):
    # TODO: Handle relations correctly.
    features = []
    for elm in elements:
        if elm.type() not in ['node', 'way', 'relation']:
            continue
        center = latlong(elm)
        if center:
            geometry = {'type': 'Point', 'coordinates': [center[1], center[0]]}
        else:
            continue
        #try:
        #    geometry = elm.geometry()
        #except:
        #    continue
        popup = '<b>{}</b><br>lat: {} lon: {}<br>{}'.format(
            element_name(elm), elm.lat(), elm.lon(),
            '<br>'.join('{}: {}'.format(key, val)
                        for key, val in elm.tags().items())
        )
        feature = {
            'type': 'Feature',
            'geometry': geometry,
            'properties': {
                'popupContent': popup
            }
        }
        features.append(feature)
    return {'type': 'FeatureCollection', 'features': features}


def merge_feature_collections(*feature_collections):
    features = list(itertools.chain.from_iterable(
        coll['features'] for coll in feature_collections))
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
    elif isinstance(qtype, tuple) and qtype[0] == 'findkey':
        # TODO: Handle multiple keys
        key = qtype[1]
        name = lambda elm: ('{} {}'.format(elm.type(), elm.id())
                            if key == 'name' else element_name(elm))
        values = ['{}: {}'.format(name(elm), str(elm.tag(key)))
                  for elm in elements]
        return {'type': 'list', 'list': values}
    return {'type': 'error', 'error': 'Unknown qtype: {}'.format(qtype)}


def overpass_query(features, template_name):
    template = ENV.get_template(template_name)
    ql = template.render(features=features)
    print(ql)
    try:
        result = OVERPASS.query(ql)
    except:
        traceback.print_exc()
        ans = {'type': 'error',
               'error': 'Error when retrieving result. Maybe a Timeout?'}
        return ans
    return result


def nominatim_query(query):
    try:
        result = NOMINATIM.query(query)
    except Exception as e:
        traceback.print_exc()
        raise AnsweringError('Error when contacting Nominatim.') from e
    return result


def add_area_id(features):
    area = features.get('area')
    if area:
        n_result = nominatim_query(area)
        area_id = n_result.areaId()
        if area_id:
            features['area_id'] = area_id


def limit_to_closest(centers, targets, limit, max_dist):
    # max_dist has to be in km

    ids_closest_to_some_center = set()
    target_coords_by_id = {
        target.id(): latlong(target) for target in targets
    }
    target_id_min_dist_by_center_id = defaultdict(lambda: (None, math.inf))
    for center in centers:
        center_coords = latlong(center)
        ids_and_dists = []
        for id, target_coords in target_coords_by_id.items():
            dist = geodesic(target_coords, center_coords).kilometers
            if dist <= max_dist:
                ids_and_dists.append((id, dist))
                _, min_dist = target_id_min_dist_by_center_id[center.id()]
                if dist < min_dist:
                    target_id_min_dist_by_center_id[center.id()] = (id, dist)

        for id, dist in sorted(ids_and_dists,
                               key=lambda id_dist: id_dist[1])[:limit]:
            ids_closest_to_some_center.add(id)

    closest_targets = [
        target for target in targets
        if target.id() in ids_closest_to_some_center
    ]

    target_id_min_dist = [target_id_min_dist_by_center_id[center.id()]
                          for center in centers]
    return closest_targets, target_id_min_dist


def handle_around_topx(elements, features):
    centers = []
    targets = elements
    target_id_min_dist = []
    around_topx = features.get('around_topx')
    if around_topx:
        try:
            limit_to = int(str(around_topx))
        except ValueError:
            logging.error('Invalid around_topx value in features: {}'
                          .format(features))
            limit_to = None

        for i, elm in enumerate(elements):
            if elm.type() == 'separator':
                centers = elements[:i]
                targets = elements[i+1:]
                break

        if limit_to:
            max_dist = int(DISTS.get(str(features['maxdist']),
                                     str(features['maxdist'])))
            max_dist /= 1000  # Convert to km
            targets, target_id_min_dist = limit_to_closest(
                centers, targets, limit_to, max_dist)

    return centers, targets, target_id_min_dist


def answer_simple_query(features):
    if features['query_type'] == 'dist' and len(features['sub']) == 1:
        # dist_closest
        dist = True
        features = features['sub'][0]
    else:
        dist = False

    add_area_id(features)

    template_name = features['query_type'] + '.jinja2'
    o_result = overpass_query(features, template_name)
    elements = o_result.elements()

    centers, targets, target_id_min_dist = handle_around_topx(elements,
                                                              features)
    elements = list(itertools.chain(centers, targets))

    ans = {'type': 'sub', 'sub': [], 'targets': geojson(targets)}
    if centers:
        ans['centers'] = geojson(centers)
    if dist:
        targets_by_id = {target.id(): target for target in targets}
        for center, (target_id, min_dist) in zip(centers, target_id_min_dist):
            if target_id:
                a = {'type': 'dist', 'dist': min_dist,
                     'center': (center.id(), element_name(center)),
                     'target': (target_id,
                                element_name(targets_by_id[target_id]))}
                ans['sub'].append(a)
    else:
        for qtype in features['qtype']:
            ans['sub'].append(apply_qtype(qtype, targets))
    return ans, centers, targets


def answer_dist_between_query(features):
    _, _, centers = answer_simple_query(features['sub'][0])
    _, _, targets = answer_simple_query(features['sub'][1])

    if centers and targets:
        center = centers[0]
        target = targets[0]
        centers = [center]
        targets = [target]
        dist = geodesic(latlong(center), latlong(target)).kilometers
        ans = {'type': 'dist', 'dist': dist,
               'center': (center.id(), element_name(center)),
               'target': (target.id(), element_name(target)),
               'centers': geojson(centers),
               'targets': geojson(targets)}
    else:
        ans = {'type': 'error'}
        if centers:
            error =  'No result for query 2.'
            ans['centers'] = geojson(centers)
        elif targets:
            error =  'No result for query 1.'
            ans['targets'] = geojson(targets)
        else:
            error =  'No result, neither for query 1 nor for query 2.'
        ans['error'] = error

    return ans, centers, targets


def answer(features):
    if features:
        print(features)
        features = transform_features(features, canonicalize_nwr_features)
        features = transform_features(features, add_name_tags)
        print(features)

        if features['query_type'] in ['around_query', 'in_query']:
            ans, _, _ = answer_simple_query(features)
            return ans
        elif features['query_type'] == 'dist' and len(features['sub']) == 1:
            ans, _, _ = answer_simple_query(features)
            return ans
        elif features['query_type'] == 'dist' and len(features['sub']) == 2:
            ans, _, _ = answer_dist_between_query(features)
            return ans
        error = 'query_type {} not supported yet'.format(
            features['query_type'])
    else:
        error = 'No features given'

    return {
        'type': 'error',
        'error': error
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
    ans = answer(features)
    if 'geojson' in ans:
        print('Dropping geojson')
        del ans['geojson']
    print(ans)


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

