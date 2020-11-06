#!/usr/bin/env python3

import argparse
from collections import defaultdict, namedtuple
import re

import requests

# This is supposed to select older versions, but I didn’t get it to work.
#DEFAULT_URL = 'https://wiki.openstreetmap.org/w/index.php?title=Special:Export&pages=Nominatim%2FSpecial_Phrases%2FEN&limit=1&offset=2020-10-15T13:18:00Z&curonly=&action=submit'

DEFAULT_URL = 'https://wiki.openstreetmap.org/wiki/Special:Export/Nominatim/Special_Phrases/EN'

PhraseTableLine = namedtuple('PhraseTableLine', ['phrase', 'key', 'value', 'operator', 'plural'])

ThingTableLine = namedtuple('ThingTableLine', ['singular', 'plural', 'tags'])


def is_plural_of(sg, pl_cand):
    return (
        pl_cand == sg
        or pl_cand == sg + 's'
        or pl_cand == sg + 'es'
        or (
            pl_cand.endswith('a') and sg.endswith('um')
            and pl_cand[:-1] == sg[:-2]
        ) or (
            pl_cand.endswith('ys') and sg.endswith('y')
            and pl_cand[:-2] == sg[:-1]
        ) or (
            pl_cand.endswith('ies') and sg.endswith('y')
            and pl_cand[:-3] == sg[:-1]
        )
    )


def init_thing_table(phrase_table_lines):
    table = []
    for ptl in phrase_table_lines:
        if ptl.operator == '-':
            tag = (ptl.key, ptl.value)
            if ptl.plural:
                ttl = ThingTableLine(
                    singular=set(), plural={ptl.phrase.lower()}, tags={tag}
                )
            else:
                ttl = ThingTableLine(
                    singular={ptl.phrase.lower()}, plural=set(), tags={tag}
                )
            table.append(ttl)
    return table


def merge_lines(table, criterion):
    for i in range(len(table)):
        if table[i] is None:
            continue
        for j in range(len(table) - 1, i, -1):
            if table[j] is None:
                continue
            l1 = table[i]
            l2 = table[j]
            if criterion(l1, l2):
                table[i] = ThingTableLine(
                    singular=l1.singular.union(l2.singular),
                    plural=l1.plural.union(l2.plural),
                    tags=l1.tags.union(l2.tags)
                )
                table[j] = None

    table = [line for line in table if line is not None]

    return table


def make_thing_table(phrase_table_lines):
    table = init_thing_table(phrase_table_lines)

    table = merge_lines(
        table,
        criterion=lambda line1, line2: line1.tags.intersection(line2.tags)
    )

    def has_singular_plural_match(line1, line2):
        for sg in line1.singular:
            for pl_cand in line2.plural:
                if is_plural_of(sg, pl_cand):
                    return True
            for sg2 in line2.singular:
                if sg == sg2:
                    return True

        for sg in line2.singular:
            for pl_cand in line1.plural:
                if is_plural_of(sg, pl_cand):
                    return True
            for sg1 in line1.singular:
                if sg == sg1:
                    return True

        return False

    table = merge_lines(table, criterion=has_singular_plural_match)

    return table


def pre_edit_phrase_table_lines(phrase_table_lines):
    lines = []
    for ptl in phrase_table_lines:
        # Phrase food merges restaurants and fast food, delete for now.
        if ptl.phrase == 'food':
            continue

        # This merges wine shop and off license, delete for now.
        if ptl.key == 'shop' and ptl.value == 'wine':
            continue

        # This merges shop=convenience|deli|supermarket, delete for now.
        if ptl.phrase in ['food shop', 'food store',
                          'food shops', 'food stores']:
            continue

        # This merges amenity=drinking_water and natural=water delete for now.
        if ptl.phrase == 'water' and ptl.value == 'drinking_water':
            continue

        # Pubs are not bars, and vice versa.
        if ptl.key == 'amenity' and ptl.value == 'bar':
            if 'pub' in ptl.phrase:
                continue
        if ptl.key == 'amenity' and ptl.value == 'pub':
            if 'bar' in ptl.phrase:
                continue

        # Place of worship is false in Special Phrases.
        if ptl.key == 'amenity' and ptl.value == 'place_of_worship':
            continue

        # Building tags are strange for this.
        if ptl.key == 'building' and ptl.value in ['hotel', 'stadium']:
            continue

        lines.append(ptl)

    return lines


def tags_to_nwr(tags):
    # Group vals of same key under one tag.
    # E.g. [('shop', 'alcohol'), ('shop', 'wine')]
    # -> [('shop', ('or', 'alcohol', 'wine'))]
    vals_by_key = defaultdict(set)
    for key, val in tags:
        vals_by_key[key].add(val)
    tags = []
    for key, vals in vals_by_key.items():
        if len(vals) == 1:
            tags.append((key, vals.pop()))
        else:
            tags.append((key, ('or', *sorted(vals))))

    # Form a suitable nwr value out of the tags.
    if len(tags) == 1:
        tags = [tags.pop()]
    elif len(tags) > 1:
        tags = [('or', *sorted(tags))]
    else:
        raise ValueError('Empty tags: {}'.format(tags))
    return tags


def post_edit_thing_table(table):
    for ttl in table:
        ttl.tags.discard(('building', 'hotel'))
        ttl.tags.discard(('building', 'stadium'))

    table.append(ThingTableLine(
        singular={'food'}, plural={'food'},
        tags={('amenity', 'restaurant'), ('amenity', 'fast_food')}
    ))

    table.append(ThingTableLine(
        singular={'food shop', 'food store'},
        plural={'food shops', 'food store'},
        tags={('shop', 'convenience'), ('shop', 'deli'),
              ('shop', 'supermarket')}
    ))

    table.append(ThingTableLine(
        singular={'wine shop'}, plural={'wine shops'}, tags={('shop', 'wine')}
    ))

    table.append(ThingTableLine(
        singular={'place of worship'}, plural={'places of worship'},
        tags={('amenity', 'place_of_worship')}
    ))


    for i, ttl in enumerate(table):
        # Asking for off license also yields wine shop, but not vice versa.
        if 'off license' in ttl.singular:
            ttl.tags.add(('shop', 'wine'))

        if 'water' in ttl.singular:
            ttl.tags.add(('amenity', 'drinking_water'))
            ttl.tags.add(('drinking_water', 'yes'))

        tags = tags_to_nwr(ttl.tags)

        # Discard building=church etc. because these tags are more sensible.
        # They are not in special phrases because double tags are not supported
        # there.
        if 'church' in ttl.singular:
            tags = [('amenity', 'place_of_worship'), ('religion', 'christian')]
        elif 'mosque' in ttl.singular:
            tags = [('amenity', 'place_of_worship'), ('religion', 'muslim')]
        elif 'synagogue' in ttl.singular:
            tags = [('amenity', 'place_of_worship'), ('religion', 'jewish')]

        table[i] = ThingTableLine(
            singular=ttl.singular, plural=ttl.plural, tags=tags
        )

    for denomination in ['anglican', 'catholic', 'orthodox', 'protestant']:
        table.append(ThingTableLine(
            singular={denomination + ' church'},
            plural={denomination + ' churchs', denomination + ' churches'},
            tags=[('amenity', 'place_of_worship'), ('denomination', denomination)]
        ))

    return table


def get_phrase_table_lines(wiki_page: str):
    line_regex = r'^\|(?P<phrase>[^|]+)\|\|(?P<key>[^|]+)\|\|(?P<value>[^|]+)\|\|(?P<operator>[^|]+)\|\|(?P<plural>[ YN-]+)$'
    phrase_table_lines = []
    for line in wiki_page.split('\n'):
        m = re.match(line_regex, line)
        if m:
            phrase_table_lines.append(PhraseTableLine(
                phrase=m.group('phrase').strip().lower(),
                key=m.group('key').strip(),
                value=m.group('value').strip(),
                operator=m.group('operator').strip(),
                plural=m.group('plural').strip() == 'Y',
            ))
    return phrase_table_lines


def get_wiki_page(file=None, url=DEFAULT_URL):
    if file:
        with open(file) as f:
            content = f.read()
    else:
        resp = requests.get(url)
        content = resp.text
    return content

def get_phrase_to_tags(phrase_table_lines):
    phrase_to_tags = defaultdict(set)
    for ptl in phrase_table_lines:
        tag = '{}={}'.format(ptl.key, ptl.value)
        phrase_to_tags[ptl.phrase].add(tag)
    return phrase_to_tags


def action_table(file=None, url=DEFAULT_URL):
    wiki_page = get_wiki_page(file, url)
    phrase_table_lines = get_phrase_table_lines(wiki_page)
    table = make_thing_table(
        pre_edit_phrase_table_lines(phrase_table_lines)
    )
    table = post_edit_thing_table(table)
    return table


def action_duplicates(file=None, url=DEFAULT_URL):
    wiki_page = get_wiki_page(file, url)
    phrase_table_lines = get_phrase_table_lines(wiki_page)
    phrase_to_tags = get_phrase_to_tags(phrase_table_lines)
    tags_to_phrases = defaultdict(set)
    for phrase, tags in phrase_to_tags.items():
        if len(tags) > 1:
            tags_to_phrases[tuple(sorted(tags))].add(phrase)
    return tags_to_phrases


def action_tags(file=None, url=DEFAULT_URL):
    wiki_page = get_wiki_page(file, url)
    phrase_table_lines = get_phrase_table_lines(wiki_page)
    phrase_to_tags = get_phrase_to_tags(phrase_table_lines)
    all_tags = sorted({tag for tags in phrase_to_tags.values() for tag in tags})
    return all_tags


def main(action, file=None, url=DEFAULT_URL):
    if action == 'table':
        table = action_table(file, url)
        for ttl in table:
            print(
                '{singular} | {plural} | {tags}'
                .format(
                    singular=', '.join(sorted(ttl.singular)),
                    plural=', '.join(sorted(ttl.plural)),
                    tags=ttl.tags
                    #tags=', '.join(sorted('{}={}'.format(key, val)
                    #                      for key, val in ttl.tags)),
                )
            )

    elif action == 'duplicates':
        tags_to_phrases = action_duplicates(file, url)
        for tags, phrases in tags_to_phrases.items():
            print('{}: {}'.format(
                ', '.join(tags),
                ', '.join(phrases),
            ))

    else:
        all_tags = action_tags(file, url)
        for tag in all_tags:
            print(tag)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['tags', 'duplicates', 'table'])
    parser.add_argument('--url', '-u', default=DEFAULT_URL)
    parser.add_argument('--file', '-f')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    ARGS = parse_args()
    main(**vars(ARGS))
