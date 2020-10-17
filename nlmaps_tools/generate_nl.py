from collections import defaultdict
from pathlib import Path
import os
import re
import random

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
              / 'en_templates' / subdir_basename)
    for template in os.listdir(subdir):
        prefix = template.split('_')[0]
        templates[prefix].add('{}/{}'.format(subdir_basename, template))
    return templates


COMMON_TEMPLATES = collect_templates('common')
IN_QUERY_ONLY_TEMPLATES = collect_templates('in_query')
AROUND_QUERY_ONLY_TEMPLATES = collect_templates('around_query')

IN_QUERY_TEMPLATES = merge_templates(COMMON_TEMPLATES, IN_QUERY_ONLY_TEMPLATES)
AROUND_QUERY_TEMPLATES = merge_templates(COMMON_TEMPLATES,
                                         AROUND_QUERY_ONLY_TEMPLATES)

shorthand_to_qtype = {
    'name': (('findkey', 'name'),),
    'latlong': (Symbol('latlong'),),
    'least1': (('least', ('topx', Symbol('1'))),),
    'count': (Symbol('count'),),
    'website': (('findkey', 'website'),),
    'opening_hours': (('findkey', 'opening_hours'),),
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
    loader=jinja2.PackageLoader('nlmaps_tools', 'en_templates'),
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
)


ENV.globals['choose'] = choose
ENV.globals['optional'] = optional
ENV.globals['sym_str_equal'] = sym_str_equal
ENV.globals['int'] = int


def remove_superfluous_whitespace(s):
    return re.sub(r'\s+', ' ', s).strip()


def choose_poi():
    poi = choose(['École Maternelle Diderot', 'Place Tirant Lo Blanc',
                  'Westerweiden (Airbus)', "Rue d'Agier", 'Route Léon Lachamp'])
    return [('name', poi)]


def generate_features(thing_table):
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

    features['area'] = choose(['Kreuzberg', 'Berlin',
                               'Heidelberg', 'Schwäbisch Hall'])

    features['query_type'] = choose(['around_query', 'in_query'], [0.6, 0.4])
    features['cardinal_direction'] = choose(
        [None, 'east', 'north', 'south', 'west'],
        [0.7, 0.075, 0.075, 0.075, 0.075]
    )

    if features['query_type'] == 'around_query':
        if features['cardinal_direction']:
            features['maxdist'] = Symbol('DIST_OUTTOWN')
        else:
            features['maxdist'] = choose(
                [Symbol('DIST_INTOWN'), Symbol('DIST_OUTTOWN'),
                 Symbol('WALKING_DIST'), Symbol('DIST_DAYTRIP'),
                 str(random.randint(1, 100)) + '000'],
                [0.3, 0.25, 0.2, 0.1, 0.15]
            )

        if optional('nwr_and_area', 0.75):
            features['center_nwr'] = choose_poi()
        else:
            if optional('area_as_nwr', 0.5):
                features['center_nwr'] = [('name', features['area'])]
            else:
                features['center_nwr'] = choose_poi()
            del features['area']

    rfeatures['qtype_shorthand'] = choose(
        ['name', 'latlong', 'least1', 'count', 'website', 'opening_hours'],
        [0.3, 0.2, 0.2, 0.2, 0.00, 0.00]
        #[0.3, 0.2, 0.2, 0.2, 0.05, 0.05]
    )

    features['qtype'] = shorthand_to_qtype[rfeatures['qtype_shorthand']]

    return features


def generate_en(features):
    if features['query_type'] == 'in_query':
        templates = IN_QUERY_TEMPLATES
    elif features['query_type'] == 'around_query':
        templates = AROUND_QUERY_TEMPLATES
    else:
        templates = COMMON_TEMPLATES
    rfeatures = features['rendering_features']
    possible_templates = templates[rfeatures['qtype_shorthand']]
    template = ENV.get_template(choose(possible_templates))
    return remove_superfluous_whitespace(
        template.render(features=features, **rfeatures)
    )


def main():
    thing_table = special_phrases_table()
    for i in range(1000):
        features = generate_features(thing_table)
        print(generate_en(features))
        print(generate_mrl(features))
        print()


if __name__ == '__main__':
    main()
