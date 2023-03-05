import argparse
from collections import defaultdict
import itertools
import json
import logging
import math
import sys
import traceback
from urllib.error import HTTPError

from geopy.distance import geodesic
import jinja2
from OSMPythonTools.nominatim import Nominatim

from nlmaps_tools.parse_mrl import MrlGrammar, Symbol
from nlmaps_tools.overpass_round_robin import OverpassRoundRobin

USER_AGENT = 'NLMaps Web (https://nlmaps.gorgor.de/)'
NOMINATIM = Nominatim(userAgent=USER_AGENT, waitBetweenQueries=1)
OVERPASS = OverpassRoundRobin(userAgent=USER_AGENT, waitBetweenQueries=1)

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


def get_tags_in_nwr_features(nwr_features, exclude=tuple()):
    tags = []
    for feat in nwr_features:
        if feat[0] in ['or', 'and'] and isinstance(feat[1], (list, tuple)):
            for key, val in feat[1:]:
                if key not in exclude:
                    tags.append((key, val))
        elif (len(feat) == 2 and isinstance(feat[1], (list, tuple))
              and feat[1][0] == 'or'):
            for val in feat[1][1:]:
                if feat[0] not in exclude:
                    tags.append((feat[0], val))
        elif len(feat) == 2 and all(isinstance(f, str) for f in feat):
            if feat[0] not in exclude:
                tags.append((feat[0], feat[1]))
        else:
            raise ValueError('Unexpected feature part: {}'.format(feat))

    return tags


# This does not properly deal with nested ors, but that is not really supported
# currently anyway.
def canonicalize_nwr_features(nwr_features):
    parts = []
    for feat in nwr_features:
        if feat[0] in ['or', 'and'] and isinstance(feat[1], (list, tuple)):
            without_nested_ors = []
            for part in canonicalize_nwr_features(feat[1:]):
                if part[0] == 'or':
                    without_nested_ors.extend(part[1:])
                else:
                    without_nested_ors.append(part)
            parts.append((feat[0], *without_nested_ors))
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


def contains(bbox, coords):
    minlat, maxlat, minlon, maxlon = bbox
    lat, lon = coords
    return minlat <= lat <= maxlat and minlon <= lon <= maxlon


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
        coll['features'] for coll in feature_collections if coll))
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
    logging.info('Querying Overpass: {}'.format(ql))
    try:
        result = OVERPASS.query(ql)
    except HTTPError as exc:
        traceback.print_exc()
        if exc.code == 429:
            error = 'Too Many Requests to Overpass API.'
        elif exc.code == 504:
            error = 'Gateway Timeout at Overpass API.'
        else:
            error = 'HTTP Error with Overpass API.'
        ans = {'type': 'error', 'error': error}
        return ans
    except:
        traceback.print_exc()
        ans = {'type': 'error', 'error': 'Error when retrieving result.'}
        return ans
    return result


def nominatim_query(query, params=None):
    params = params or {}
    logging.info('Querying Nominatim: q={}, params={}'
                 .format(query, params))
    try:
        result = NOMINATIM.query(query, params=params)
    except Exception as e:
        traceback.print_exc()
        raise AnsweringError('Error when contacting Nominatim.') from e
    return result


def get_first_area(nominatim_result):
    for d in nominatim_result._json:
        if 'osm_type' in d and d['osm_type'] == 'relation' and 'osm_id' in d:
            area_id = 3600000000 + int(d['osm_id'])
            return d, area_id
    return None, None


def add_area_id(features):
    area = features.get('area')
    if area:
        n_result = nominatim_query(area)
        area_id = n_result.areaId()
        if area_id:
            logging.info(
                'Nominatim query for area {!r} yielded area ID {}.'
                .format(area, area_id)
            )
            features['area_id'] = area_id
            return n_result
    logging.warning(
        'Nominatim query for area {!r} did not yield an area ID.'
        .format(area)
    )
    return None


def nwr_nominatim_lookup(nwr_features, bbox=None):
    """
    bbox is a 4-tuple of minlon, minlat, maxlon, maxlat.
    """
    new_nwr_features = None
    n_result = None

    tags = get_tags_in_nwr_features(
        nwr_features, exclude=('int_name', 'alt_name', 'name:en'))
    if len(tags) == 1 and tags[0][0] == 'name':
        name = tags[0][1]

        if bbox:
            params = {
                'viewbox': '{b[0]},{b[1]},{b[2]},{b[3]}'.format(b=bbox),
                'bounded': '1'
            }
        else:
            params = None

        n_result = nominatim_query(name, params=params)
        results = n_result.toJSON()
        if results:
            new_tag = (results[0]['osm_type'], results[0]['osm_id'])
            new_nwr_features = [new_tag]

    return new_nwr_features, n_result


def substitute_name_tags(features, area_n_result):
    bbox = None
    if area_n_result:
        area, _ = get_first_area(area_n_result)
        if area:
            bbox = area['boundingbox']
            # from (minlat, maxlat, minlon, maxlon)
            # to (minlon, minlat, maxlon, maxlat)
            bbox = (bbox[2], bbox[0], bbox[3], bbox[1])

    center_nwr = features.get('center_nwr')
    target_nwr = features.get('target_nwr')
    if center_nwr:
        new_center_nwr, _ = nwr_nominatim_lookup(center_nwr, bbox=bbox)
        if new_center_nwr:
            features['center_nwr'] = new_center_nwr
    elif target_nwr:
        new_target_nwr, _ = nwr_nominatim_lookup(target_nwr, bbox=bbox)
        if new_target_nwr:
            features['target_nwr'] = new_target_nwr


def chop_to_cardinal_direction(elements, bbox, cardinal_direction):
    minlat, maxlat, minlon, maxlon = bbox
    if cardinal_direction == 'north':
        minlat = minlat + (maxlat - minlat) / 2
    elif cardinal_direction == 'east':
        if minlon == -180 and minlat == 180:
            pass
            # TODO: Handle case where area spans 180 ° meridian.
        else:
            minlon = minlon + (maxlon - minlon) / 2
    elif cardinal_direction == 'south':
        maxlat = maxlat - (maxlat - minlat) / 2
    elif cardinal_direction == 'west':
        if minlon == -180 and minlat == 180:
            pass
            # TODO: Handle case where area spans 180 ° meridian.
        else:
            maxlon = maxlon - (maxlon - minlon) / 2

    remaining_elements = []
    for elm in elements:
        coords = latlong(elm)
        if coords and not contains((minlat, maxlat, minlon, maxlon), coords):
            continue
        remaining_elements.append(elm)
    return remaining_elements


def cardinal_direction_applies(center_coords, target_coords,
                               cardinal_direction=None):
    if not cardinal_direction:
        return True
    center_lat, center_lon = center_coords
    target_lat, target_lon = target_coords
    if cardinal_direction == 'north':
        return target_lat >= center_lat
    elif cardinal_direction == 'east':
        return target_lon >= center_lon
    elif cardinal_direction == 'south':
        return target_lat <= center_lat
    elif cardinal_direction == 'west':
        return target_lon <= center_lon


def limit_to_centers(centers, targets, max_dist, max_targets,
                     cardinal_direction):
    # max_dist has to be in km
    ids_of_allowed_targets = set()
    target_coords_by_id = {
        target.id(): latlong(target) for target in targets
    }
    target_id_min_dist_by_center_id = defaultdict(lambda: (None, math.inf))
    for center in centers:
        center_coords = latlong(center)
        ids_and_dists = []
        for id, target_coords in target_coords_by_id.items():
            dist = geodesic(target_coords, center_coords).kilometers
            if dist <= max_dist and cardinal_direction_applies(
                    center_coords, target_coords, cardinal_direction):
                ids_and_dists.append((id, dist))
                _, min_dist = target_id_min_dist_by_center_id[center.id()]
                if dist < min_dist:
                    target_id_min_dist_by_center_id[center.id()] = (id, dist)

        if max_targets:
            ids_and_dists.sort(key=lambda id_dist: id_dist[1])
            ids_and_dists = ids_and_dists[:max_targets]
        for id, dist in ids_and_dists:
            ids_of_allowed_targets.add(id)

    closest_targets = [
        target for target in targets
        if target.id() in ids_of_allowed_targets
    ]

    target_id_min_dist = [target_id_min_dist_by_center_id[center.id()]
                          for center in centers]
    return closest_targets, target_id_min_dist


def handle_around_topx(elements, features):
    centers = []
    targets = elements
    target_id_min_dist = []

    for i, elm in enumerate(elements):
        if elm.type() == 'separator':
            print(i, elm, 'FOUND SEP')
            centers = elements[:i]
            targets = elements[i+1:]
            break

    around_topx = features.get('around_topx')
    max_targets = None
    if around_topx:
        try:
            max_targets = int(str(around_topx))
        except ValueError:
            logging.error('Invalid around_topx value in features: {}'
                          .format(features))

    cardinal_direction = features.get('cardinal_direction')
    print('ENTERING?', max_targets, cardinal_direction)
    print('CEN&TAR', len(centers), len(targets))
    if max_targets or cardinal_direction:
        max_dist = int(DISTS.get(str(features['maxdist']),
                                 str(features['maxdist'])))
        max_dist /= 1000  # Convert to km
        targets, target_id_min_dist = limit_to_centers(
            centers, targets, max_dist, max_targets,
            cardinal_direction
        )
        print('CEN&TAR', len(centers), len(targets))

    return centers, targets, target_id_min_dist


def answer_simple_query(features):
    if features['query_type'] == 'dist' and len(features['sub']) == 1:
        # dist_closest
        dist = True
        features = features['sub'][0]
    else:
        dist = False

    n_result = add_area_id(features)

    template_name = features['query_type'] + '.jinja2'
    substitute_name_tags(features, n_result)
    o_result = overpass_query(features, template_name)
    if isinstance(o_result, dict):
        # There was an error and the query function directly returned our
        # answer.
        ans = o_result
        return ans, [], []

    elements = o_result.elements()

    if (features['query_type'] == 'in_query'
            and features.get('cardinal_direction')
            and n_result):
        card = features['cardinal_direction']
        bbox = [float(coord) for coord in n_result.toJSON()[0]['boundingbox']]
        elements = chop_to_cardinal_direction(elements, bbox, card)

    if features['query_type'] == 'around_query':
        centers, targets, target_id_min_dist = handle_around_topx(elements,
                                                                  features)
    else:
        centers = []
        targets = elements

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
        features = transform_features(features, add_name_tags)
        features = transform_features(features, canonicalize_nwr_features)
        print(features)

        try:
            if features['query_type'] in ['around_query', 'in_query']:
                ans, _, _ = answer_simple_query(features)
                return ans
            elif features['query_type'] == 'dist' and len(features['sub']) == 1:
                ans, _, _ = answer_simple_query(features)
                return ans
            elif features['query_type'] == 'dist' and len(features['sub']) == 2:
                ans, _, _ = answer_dist_between_query(features)
                return ans
            else:
                error = 'query_type {} not supported yet'.format(
                    features['query_type'])
        except Exception as exc:
            if len(exc.args) > 0:
                error = exc.args[0]
            else:
                error = 'Unknown MRL interpretation error'
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
            features = parseResult['features']

    elif isinstance(mrl, dict) and 'query_type' in mrl:
        features = mrl

    else:
        try:
            features = json.loads(mrl)
        except:
            return None
    return features


def main(mrl, escaped=False):
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
    )
    features = load_features(mrl, escaped=escaped)
    logging.info(features)
    ans = answer(features)
    if 'geojson' in ans:
        logging.info('Dropping geojson')
        del ans['geojson']
    logging.info(ans)


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

