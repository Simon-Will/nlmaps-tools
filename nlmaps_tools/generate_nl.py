import argparse
from collections import defaultdict
import itertools
from pathlib import Path
import os
import re
import random
import sys

import jinja2

from nlmaps_tools.generate_mrl import generate_from_features as generate_mrl
from nlmaps_tools.parse_mrl import Symbol
from nlmaps_tools.special_phrases import action_table as special_phrases_table


def merge_templates(templ1, templ2):
    return {
        key: set.union(
            templ1[key] if key in templ1 else set(),
            templ2[key] if key in templ2 else set(),
        )
        for key in set.union(set(templ1.keys()), set(templ2.keys()))
    }


def collect_templates(subdir_basename):
    templates = defaultdict(set)
    subdir = (Path(os.path.dirname(os.path.abspath(__file__)))
              / 'nl_templates' / subdir_basename)
    for template in os.listdir(subdir):
        prefix = template.split('_')[0]
        templates[prefix].add('{}/{}'.format(subdir_basename, template))
    return templates


COMMON_TEMPLATES = collect_templates('common')
IN_QUERY_ONLY_TEMPLATES = collect_templates('in_query')
AROUND_QUERY_ONLY_TEMPLATES = collect_templates('around_query')
DIST_SAME_AREA_ONLY_TEMPLATES = collect_templates('dist_same_area')

NAMED_IN_QUERY_TEMPLATES = collect_templates('named_in_query')
CLOSEST_AROUND_QUERY_TEMPLATES = collect_templates('closest_around_query')
DIST_CLOSEST_TEMPLATES = collect_templates('dist_closest')
DIST_DIFF_AREA_TEMPLATES = collect_templates('dist_diff_area')

IN_QUERY_TEMPLATES = merge_templates(COMMON_TEMPLATES, IN_QUERY_ONLY_TEMPLATES)
AROUND_QUERY_TEMPLATES = merge_templates(COMMON_TEMPLATES,
                                         AROUND_QUERY_ONLY_TEMPLATES)
DIST_SAME_AREA_TEMPLATES = merge_templates(DIST_SAME_AREA_ONLY_TEMPLATES,
                                           DIST_DIFF_AREA_TEMPLATES)

SHORTHAND_TO_QTYPE = {
    'name': (('findkey', 'name'),),
    'latlong': (Symbol('latlong'),),
    'least1': (('least', ('topx', Symbol('1'))),),
    'count': (Symbol('count'),),
    'website': (('findkey', 'website'),),
    'opening-hours': (('findkey', 'opening_hours'),),
}


def choose(population, weights=None):
    if not weights and not isinstance(population, (tuple, list)):
        population = list(population)

    return random.choices(population=population, weights=weights)[0]


def optional(token, chance_to_use=None):
    weights = [chance_to_use, 1 - chance_to_use] if chance_to_use else None
    return choose([token, ''], weights=weights)


def sym_str_equal(obj1, obj2):
    s1 = obj1.string if isinstance(obj1, Symbol) else obj1
    s2 = obj2.string if isinstance(obj2, Symbol) else obj2
    return s1 == s2


ENV = jinja2.Environment(
    loader=jinja2.PackageLoader('nlmaps_tools', 'nl_templates'),
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
)


ENV.globals['choose'] = choose
ENV.globals['optional'] = optional
ENV.globals['sym_str_equal'] = sym_str_equal
ENV.globals['int'] = int


def remove_superfluous_whitespace(s):
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) > 1 and s[-1] in ['.', '!', '?'] and s[-2] == ' ':
        s = s[:-2] + s[-1]
    return s


def add_noise(s, exclude=tuple(), noise_chance=0.01):
    excluded_indices = set()
    for exc in exclude:
        if exc in s:
            start = s.index(exc)
            # Add the indices of the excluded string
            # and also 1 character before and after it.
            excluded_indices.update(range(start - 1, start + len(exc) + 1))
        else:
            print('Error: {exc!r} is not in {s!r}'.format(exc=exc, s=s),
                  file=sys.stderr)

    alphabet = [chr(n) for n in itertools.chain(range(0x41, 0x41 + 26),
                                                range(0x61, 0x61 + 26))]

    new = [
        choose(alphabet)
        if i not in excluded_indices and optional('add_noise', noise_chance)
        else char
        for i, char in enumerate(s)
    ]
    return ''.join(new)


def choose_poi(pois):
    poi = choose(pois)
    return [('name', poi)]


def generate_features(thing_table, areas, pois):
    if optional('dist', 0.2):
        return generate_dist_query_features(thing_table, areas, pois)
    return generate_poi_query_features(thing_table, areas, pois)


def generate_dist_query_features(thing_table, areas, pois):
    rfeatures = {'qtype_shorthand': 'dist'}
    features = {'rendering_features': rfeatures, 'query_type': 'dist'}
    if optional('closest'):
        around_query = generate_tag_query_features(thing_table, areas, pois,
                                                   closest=True)
        around_query['qtype_shorthand'] = 'latlong'
        around_query['qtype'] = SHORTHAND_TO_QTYPE['latlong']
        features['sub'] = [around_query]
        rfeatures['dist_type'] = 'closest'
        rfeatures['plural'] = around_query['rendering_features']['plural']
        rfeatures['thing_singular'
                  ] = around_query['rendering_features'].get('thing_singular')
        rfeatures['thing_plural'
                  ] = around_query['rendering_features'].get('thing_plural')
    else:
        rfeatures['dist_type'] = choose(['same_area', 'diff_area'], [0.3, 0.7])
        if rfeatures['dist_type'] == 'same_area':
            in_query_1 = generate_ne_query_features(areas, pois, with_area=True)
            in_query_2 = generate_ne_query_features(areas, pois, with_area=False)
            in_query_2['area'] = in_query_1['area']
        else:
            in_query_1 = generate_ne_query_features(areas, pois)
            in_query_2 = generate_ne_query_features(areas, pois)
        in_query_1['qtype_shorthand'] = 'latlong'
        in_query_1['qtype'] = SHORTHAND_TO_QTYPE['latlong']
        in_query_2['qtype_shorthand'] = 'latlong'
        in_query_2['qtype'] = SHORTHAND_TO_QTYPE['latlong']
        features['sub'] = [in_query_1, in_query_2]

        rfeatures['first_plural'
                  ] = in_query_1['rendering_features']['plural']
        rfeatures['first_thing_singular'
                  ] = in_query_1['rendering_features'].get('thing_singular')
        rfeatures['first_thing_plural'
                  ] = in_query_1['rendering_features'].get('thing_plural')
        rfeatures['second_plural'
                  ] = in_query_2['rendering_features']['plural']
        rfeatures['second_thing_singular'
                  ] = in_query_2['rendering_features'].get('thing_singular')
        rfeatures['second_thing_plural'

                  ] = in_query_2['rendering_features'].get('thing_plural')
    return features


def generate_poi_query_features(thing_table, areas, pois, ne=None,
                                around=None, closest=None):
    if ne or (ne is None and optional('named_entity_query', 0.05)):
        return generate_ne_query_features(areas, pois)
    else:
        return generate_tag_query_features(thing_table, areas, pois,
                                           around=around, closest=closest)


def generate_tag_query_features(thing_table, areas, pois, around=None,
                                closest=None):
    if closest is True:
        around = True
    rfeatures = {}
    features = {'rendering_features': rfeatures}

    idx = random.randint(0, len(thing_table) - 1)
    thing = thing_table[idx]
    features['target_nwr'] = thing.tags
    if thing.singular:
        rfeatures['thing_singular'] = choose(thing.singular)
        if thing.plural:
            plural_chance = 0.7
            rfeatures['thing_plural'] = choose(thing.plural)
        else:
            plural_chance = 0.0
            rfeatures['thing_plural'] = rfeatures['thing_singular']
    elif thing.plural:
        plural_chance = 1.0
        rfeatures['thing_plural'] = choose(thing.plural)
    else:
        raise ValueError('Neither singular nor plural in thing: {}'
                            .format(thing))

    rfeatures['plural'] = choose([True, False],
                                 [plural_chance, 1 - plural_chance])

    features['area'] = choose(areas)

    if around:
        features['query_type'] = 'around_query'
    elif around is False:
        features['query_type'] = 'in_query'
    else:  # around is None
        features['query_type'] = choose(['around_query', 'in_query'], [0.6, 0.4])

    if closest:
        features['cardinal_direction'] = None
    else:
        features['cardinal_direction'] = choose(
            [None, 'east', 'north', 'south', 'west'],
            [0.7, 0.075, 0.075, 0.075, 0.075]
        )

    if features['query_type'] == 'around_query':
        if features['cardinal_direction']:
            features['maxdist'] = Symbol('DIST_OUTTOWN')
        else:
            if closest or (closest is None and optional('closest', 0.3)):
                features['around_topx'] = Symbol('1')
                features['maxdist'] = Symbol('DIST_INTOWN')
                if 0 < plural_chance < 1:
                    # If the plural chance is not 0 or 1, then singular and
                    # plural forms exist. The singular should be very much
                    # preferred for the closest question type.
                    rfeatures['plural'] = choose([True, False], [0.1, 0.9])
            else:
                features['maxdist'] = choose(
                    [Symbol('DIST_INTOWN'), Symbol('DIST_OUTTOWN'),
                     Symbol('WALKING_DIST'), Symbol('DIST_DAYTRIP'),
                     Symbol(str(random.randint(1, 100)) + '000')],
                    [0.3, 0.25, 0.2, 0.1, 0.15]
                )

        if optional('nwr_and_area', 0.75):
            features['center_nwr'] = choose_poi(pois)
        else:
            if optional('area_as_nwr', 0.5):
                features['center_nwr'] = [('name', features['area'])]
            else:
                features['center_nwr'] = choose_poi(pois)
            del features['area']

    if features.get('around_topx'):
        rfeatures['qtype_shorthand'] = choose(
            ['name', 'latlong', 'website', 'opening-hours'],
            [0.4, 0.4, 0.00, 0.2]
        )
    else:
        rfeatures['qtype_shorthand'] = choose(
            ['name', 'latlong', 'least1', 'count', 'website', 'opening-hours'],
            [0.3, 0.2, 0.2, 0.2, 0.00, 0.1]
            #[0.3, 0.2, 0.2, 0.2, 0.05, 0.05]
        )

    features['qtype'] = SHORTHAND_TO_QTYPE[rfeatures['qtype_shorthand']]

    return features


def generate_ne_query_features(areas, pois, with_area=None):
    rfeatures = {'named_entity': True}
    features = {'rendering_features': rfeatures}
    features['query_type'] = 'in_query'
    rfeatures['thing_singular'] = rfeatures['thing_plural'] = choose(pois)
    features['target_nwr'] = [('name', rfeatures['thing_singular'])]
    rfeatures['plural'] = False
    if with_area is True or (with_area is None and optional('with_area', 0.6)):
        features['area'] = choose(areas)

    rfeatures['qtype_shorthand'] = choose(
        ['latlong', 'website', 'opening-hours'],
        [0.6, 0.00, 0.4]
    )
    features['qtype'] = SHORTHAND_TO_QTYPE[rfeatures['qtype_shorthand']]
    return features


def generate_nl(features, noise=False):
    rfeatures = features['rendering_features']
    if rfeatures.get('dist_type') == 'closest':
        templates = DIST_CLOSEST_TEMPLATES
    elif rfeatures.get('dist_type') == 'same_area':
        templates = DIST_SAME_AREA_TEMPLATES
    elif rfeatures.get('dist_type') == 'diff_area':
        templates = DIST_DIFF_AREA_TEMPLATES
    elif features['query_type'] == 'in_query':
        if features['rendering_features'].get('named_entity'):
            templates = NAMED_IN_QUERY_TEMPLATES
        else:
            templates = IN_QUERY_TEMPLATES
    elif features['query_type'] == 'around_query':
        if features.get('around_topx'):
            templates = CLOSEST_AROUND_QUERY_TEMPLATES
        else:
            templates = AROUND_QUERY_TEMPLATES
    else:
        templates = COMMON_TEMPLATES
    possible_templates = templates[rfeatures['qtype_shorthand']]
    template = ENV.get_template(choose(possible_templates))
    rfeatures['template'] = template  # This is only saved as debugging info.

    nl = remove_superfluous_whitespace(
        template.render(features=features, **rfeatures)
    )
    if optional('capitalize_first'):
        nl = nl[0].upper() + nl[1:]

    if noise:
        proper_names = []
        if features.get('area'):
            proper_names.append(features['area'])
        if features.get('center_nwr'):
            proper_names.append(features['center_nwr'][0][1])
        nl = add_noise(nl, exclude=proper_names)

    return nl


def omit_location(loc):
    return (
        re.match(r'^[\s\d]+$', loc)
        or len(loc) > 40
        or len(loc) < 2
        # Allow only Unicode code blocks Basic Latin, Latin-1 Supplement, Latin
        # Extended-A and Latin Extended-B as well as General Punctuation
        or any(ord(char) > 0x024f and not 0x2000 <= ord(char) <= 0x206F
               for char in loc)
    )


def main(areas, pois, count=100, escape=False, nl_suffix='en', noise=False,
         out_prefix=None):
    random.seed(42)
    with open(areas) as f:
        areas = [remove_superfluous_whitespace(line)
                 for line in f if not omit_location(line)]
    with open(pois) as f:
        pois = [remove_superfluous_whitespace(line)
                for line in f if not omit_location(line)]

    if out_prefix:
        nl_file = open(out_prefix + '.' + nl_suffix, 'w')
        mrl_file = open(out_prefix + '.mrl', 'w')
    else:
        nl_file = mrl_file = sys.stdout

    special_phrases_file = (Path(__file__)
                            / '../data/special_phrases.txt').resolve()
    thing_table = special_phrases_table(special_phrases_file)

    for _ in range(count):
        features = generate_features(thing_table, areas, pois)
        nl = generate_nl(features, noise=noise)
        mrl = generate_mrl(features, escape=escape)
        print(nl, file=nl_file)
        print(mrl, file=mrl_file)
        if not out_prefix:
            print()

    if out_prefix:
        nl_file.close()
        mrl_file.close()


def parse_args():
    description = 'Generate NLMaps training data'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('areas', help='Areas file')
    parser.add_argument('pois', help='POIs file')
    parser.add_argument('--count', '-c', default=100, type=int,
                        help='Number of instances to generate')
    parser.add_argument('--escape', default=False,
                        action='store_true',
                        help='Escape quotes and backslashes in proper names')
    parser.add_argument('--noise', default=False,
                        action='store_true', help='Apply noise to NL query.')
    parser.add_argument('--out-prefix', '-o',
                        help='Write dataset to files beginning with prefix')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    ARGS = parse_args()
    main(**vars(ARGS))
