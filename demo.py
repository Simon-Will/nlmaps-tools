#!/usr/bin/env python3

from nlmaps_tools.parse_mrl import MrlGrammar, Symbol
from nlmaps_tools.answer_mrl import (add_name_tags, canonicalize_nwr_features,
                                     ENV as overpass_ql_env, transform_features)


MRL_IN = "query(area(keyval('name','berlin')),nwr(keyval('diet:vegan',or('only','yes')),keyval('shop','*'),keyval('wheelchair','yes')),qtype(latlong))"
MRL_AROUND = "query(around(center(nwr(keyval('name','Camp Nou'))),search(nwr(keyval('amenity',or('cafe','restaurant')))),maxdist(1000)),qtype(count))"
MRL_DIST_CLOSEST = "dist(query(area(keyval('name','Michelfeld')),nwr(keyval('name','Churr')),qtype(latlong)),query(area(keyval('name','Michelfeld')),nwr(keyval('name','Hagenmueller'),keyval('shop','hairdresser')),qtype(latlong)))"
MRL_DIST_BETWEEN = "dist(query(nwr(keyval('name','HL College of commerce')),qtype(latlong)),query(nwr(keyval('name','Tapan Hospital')),qtype(latlong)))"


def main():
    mrl = MRL_AROUND
    print(mrl)
    print()

    # Parse MRL
    grammar = MrlGrammar()
    # (MRLs in the NLMaps datasets are actually never “escaped”. See
    # MrlGrammar.parseMrl for what that means.)
    parse_result = grammar.parseMrl(mrl, is_escaped=False)
    features = parse_result['features']
    print(features)
    print()

    # Add tags like int_name and alt_name
    features = transform_features(features, add_name_tags)
    print(features)
    print()

    # Canonicalize features, i.e. dissolve “or” around values into “or” around
    # tags.
    features = transform_features(features, canonicalize_nwr_features)
    print(features)
    print()

    # Render as Overpass QL
    # Does not work for MRL_DIST_*
    # For the DIST_BETWEEN, use in_query.jinja2 for each of the two sub-query
    # For the DIST_CLOSEST, use around_query.jinja2 for the one sub-query
    template_name = features['query_type'] + '.jinja2'
    template = overpass_ql_env.get_template(template_name)
    ql = template.render(features=features)
    print(ql)


if __name__ == '__main__':
    main()
