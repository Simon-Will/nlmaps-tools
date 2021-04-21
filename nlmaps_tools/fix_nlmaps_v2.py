#!/usr/bin/env python3

import argparse
import re

FINDKEY_WHITELIST = {'name', 'opening_hours', 'website'}

SUBSTITUTIONS = (
    (r"keyval\('cuisine','vegetarian'\)", r"keyval('diet:vegetarian',or('only','yes'))"),
    (r"keyval\('(historic|building)','church'\)", r"keyval('amenity','place_of_worship'),keyval('religion','christian')"),
    (r"keyval\('building','stadium'\)", r"keyval('leisure','stadium')"),
    (r"keyval\(('amenity','public_building'|'building','public')\)", r"keyval('building',or('civic','public'))"),
    (r"keyval\('building','hotel'\)", r"keyval('tourism','hotel')"),
    (r"keyval\('place','house'\)", r"keyval('building','house')"),
    (r"keyval\('place','houses'\)", r"keyval('building','house')"),
    (r"keyval\('building','train_station'\)", r"keyval('railway','station')"),
    (r"keyval\('building','yes'\)", r"keyval('building','*')"),
    (r"keyval\('historic','building'\)", r"keyval('building','*')"),
    (r"keyval\('highway','(primary_link|primary)'\)", r"keyval('highway',or('primary','primary_link'))"),
    (r"keyval\('highway','(secondary_link|secondary)'\)", r"keyval('highway',or('secondary','secondary_link'))"),
    (r"keyval\('highway','(trunk_link|trunk)'\)", r"keyval('highway',or('trunk','trunk_link'))"),
    (r"keyval\('building','farm'\)", r"keyval('building',or('farm','farm_auxiliary'))"),
    (r"keyval\('shop','alcohol'\)", r"keyval('shop',or('alcohol','wine'))"),
    # All shop=wine instances in NLMaps v2 ask for off-licence stores (and none
    # for “wine store”), which is why putting shop=alcohol|wine is alright.
    (r"keyval\('shop','wine'\)", r"keyval('shop',or('alcohol','wine'))"),
    (r"keyval\('shop','fish'\)", r"keyval('shop','seafood')"),
    (r"keyval\('shop','food'\)", r"keyval('shop',or('convenience','deli','supermarket'))"),
    (r"keyval\('wifi','free'\)", r"keyval('internet_access',or('wlan','yes'))"),
    (r"keyval\('amenity','wifi'\)", r"keyval('internet_access',or('wlan','yes'))"),
    (r"keyval\('amenity','market'\)", r"keyval('amenity','marketplace')"),
    (r"keyval\('amenity','nursery'\)", r"keyval('amenity','kindergarten')"),
    (r"keyval\(('landuse','farm'|'place','farm')\)", r"or(keyval('landuse','farmyard'),keyval('place','farm'))"),
    (r"keyval\(('landuse','wood'|'landuse','forest'|'natural','wood')\)", r"or(keyval('landuse','forest'),keyval('natural','wood'))"),
    (r"keyval\('amenity','nursing_home'\)", r"or(keyval('amenity','nursing_home'),keyval('social_facility','nursing_home'))"),
    (r"keyval\('(amenity|cuisine)','ice_cream'\)", r"or(keyval('amenity','ice_cream'),keyval('cuisine','ice_cream'))"),
    (r"keyval\('amenity','emergency_phone'\)", r"keyval('emergency','phone')"),
    (r"keyval\('shop','organic'\)", r"keyval('organic',or('only','yes'))"),
    (r"keyval\('building','shop'\)", r"keyval('shop','*')"),
    (r"keyval\('shop','fashion'\)", r"keyval('shop','clothes')"),
    (r"or\(keyval\('organic','only'\),keyval\('organic','yes'\)\)", r"keyval('organic',or('only','yes'))"),
    (r"keyval\('amenity','park'\)", r"keyval('leisure','park')"),
    (r"keyval\('amenity','atm'\)", r"or(keyval('amenity','atm'),keyval('atm','yes'))"),
    (r"keyval\('(building|historic)','tower'\)", r"keyval('man_made','tower')"),
    (r"keyval\('amenity','gym'\)", r"keyval('leisure','fitness_centre')"),
)


def fix_food(mrl, en):
    if re.search(r'\bfood\b', en, flags=re.IGNORECASE):
        regex = (
            r'((asian|british|french|german|greek|italian|spanish|fast) food'
            r'|food shop'
            r'|(glengall|spencer) food)'
        )
        if not re.search(regex, en, flags=re.IGNORECASE):
            mrl = re.sub(
                r"keyval\('amenity','(fast_food|restaurant)'\)",
                "keyval('amenity',or('fast_food','restaurant'))",
                mrl
            )

    return mrl


def fix_bar_pub(mrl, en):
    if re.search(r'\bbars?\b', en, flags=re.IGNORECASE):
        mrl = re.sub(
            r"keyval\('amenity','pub'\)",
            "keyval('amenity','bar')",
            mrl
        )
    elif re.search(r'\bpubs?\b', en, flags=re.IGNORECASE):
        mrl = re.sub(
            r"keyval\('amenity','bar'\)",
            "keyval('amenity','pub')",
            mrl
        )
    return mrl


def fix_drinking_water(mrl, en):
    if (re.search(r'\bwaters?\b', en, flags=re.IGNORECASE)
            and not re.search(r'drink', en, flags=re.IGNORECASE)):
        mrl = re.sub(
            r"keyval\(('amenity','drinking_water'|'natural','water')\)",
            "or(keyval('amenity','drinking_water'),keyval('natural','water'))",
            mrl
        )
    return mrl


def fix_area_without_center_nwr(mrl):
    if 'search(' in mrl and len(re.findall(r'\bnwr\(', mrl)) < 2:
        mrl = mrl.replace('area(', 'nwr(')
    return mrl


def has_unfixable_deprecated_tag(mrl):
    return "'shop','salon'" in mrl


def get_findkey_value(mrl):
    m = re.search(r"qtype\(findkey\('([^']+)'\)\)", mrl)
    if m:
        return m.group(1)
    return None


def main(mrl_infile, en_infile, mrl_outfile, en_outfile, quiet=False):
    deleted = 0
    modified = 0
    total = 0
    with open(mrl_infile) as mrl_inf, open(en_infile) as en_inf,\
         open(mrl_outfile, 'w') as mrl_outf, open(en_outfile, 'w') as en_outf:
        for mrl, en in zip(mrl_inf, en_inf):
            mrl = mrl.strip()
            en = en.strip()

            total += 1
            orig_mrl = mrl

            findkey_value = get_findkey_value(mrl)
            if findkey_value and findkey_value not in FINDKEY_WHITELIST:
                prefix = findkey_value.replace('_', ' ').replace(':', ' ')
                prefix += ' '
                if en.startswith(prefix):
                    if not quiet:
                        print('Deleting:', en)
                    deleted += 1
                    continue

            if has_unfixable_deprecated_tag(mrl):
                if not quiet:
                    print('Deleting:', en)
                deleted += 1
                continue

            for sub in SUBSTITUTIONS:
                mrl = re.sub(sub[0], sub[1], mrl)

            mrl = fix_food(mrl, en)
            mrl = fix_bar_pub(mrl, en)
            mrl = fix_drinking_water(mrl, en)

            mrl = fix_area_without_center_nwr(mrl)

            print(mrl, file=mrl_outf)
            print(en, file=en_outf)

            if mrl != orig_mrl:
                modified += 1

    if not quiet:
        print('Total:', total)
        print('Modified:', modified)
        print('Deleted:', deleted)


def parse_args():
    parser = argparse.ArgumentParser(description='Fix errors in NLMaps v2')
    parser.add_argument(
        'mrl_infile',
        help='NLMaps v2 MRL file'
    )
    parser.add_argument(
        'en_infile',
        help='NLMaps v2 english NL file corresponding to mrl_infile'
    )
    parser.add_argument(
        'mrl_outfile',
        help='Output file for writing the fixed mrls'
    )
    parser.add_argument(
        'en_outfile',
        help='Output file for writing the corresponding english queries'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true', default=False,
        help='Suppress information about deleted queries '
    )

    return parser.parse_args()


if __name__ == '__main__':
    ARGS = parse_args()
    main(**vars(ARGS))
