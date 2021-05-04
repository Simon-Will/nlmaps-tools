#!/usr/bin/env python3

import argparse
import json

from nlmaps_tools.parse_mrl import MrlGrammar, Symbol
from nlmaps_tools.answer_mrl import (
        add_name_tags, canonicalize_nwr_features,
        ENV as overpass_ql_env, transform_features
)


def main(nl_file, mrl_file, out_file):
    grammar = MrlGrammar()
    records = []

    with open(nl_file) as nlf, open(mrl_file) as mrlf:
        for nl_line, mrl_line in zip(nlf, mrlf):
            nl = nl_line.strip()
            mrl = mrl_line.strip()
            if mrl:
                if mrl.startswith('dist'):
                    continue
                try:
                    parse_result = grammar.parseMrl(mrl, is_escaped=False)
                except:
                    continue
                feats = parse_result['features']
                feats = transform_features(feats, add_name_tags)
                feats = transform_features(feats, canonicalize_nwr_features)
                template_name = feats['query_type'] + '.jinja2'
                template = overpass_ql_env.get_template(template_name)
                ql = template.render(features=feats, Symbol=Symbol)
                records.append({
                    'nl': nl,
                    'mrl': mrl,
                    'ql': ql
                })

    with open(out_file, 'w') as f:
        json.dump(records, f)


def parse_args():
    parser =argparse.ArgumentParser()
    parser.add_argument('nl_file')
    parser.add_argument('mrl_file')
    parser.add_argument('out_file')
    return parser.parse_args()


if __name__ == '__main__':
    ARGS = parse_args()
    main(**vars(ARGS))
