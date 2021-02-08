import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import pickle

from nlmaps_tools.special_phrases import action_tags as get_special_phrases_tags
from nlmaps_tools.parse_mrl import MrlGrammar


def read_tags(json_file):
    tags = defaultdict(set)
    with open(json_file) as f:
        content = json.load(f)
        for entry in content['data']:
            tags[entry['key']].add(entry['value'])
    return tags


def read_keys(txt_file):
    with open(txt_file) as f:
        keys = {line.strip() for line in f}
    return keys


def nwr_to_tags(nwr_features):
    tags = []
    for feat in nwr_features:
        if feat[0] in ['or', 'and'] and isinstance(feat[1], (list, tuple)):
            tags.extend(feat[1:])
        elif (len(feat) == 2 and isinstance(feat[1], (list, tuple))
              and feat[1][0] == 'or'):
            tags.extend([(feat[0], val) for val in feat[1][1:]])
        elif len(feat) == 2 and all(isinstance(f, str) for f in feat):
            tags.append((feat[0], feat[1]))
        else:
            raise ValueError('Unexpected feature part: {}'.format(feat))
    return tags


def get_tags_from_nlmaps_dataset(nlmaps_file):
    grammar = MrlGrammar()
    tags = []
    with open(nlmaps_file) as f:
        for line in f:
            mrl = line.strip()
            parse_result = grammar.parseMrl(mrl, is_escaped=False)
            features = parse_result['features']
            if 'target_nwr' in features:
                tags.extend(nwr_to_tags(features['target_nwr']))
            for sub_features in features.get('sub', []):
                if 'target_nwr' in sub_features:
                    tags.extend(nwr_to_tags(sub_features['target_nwr']))
    return tags


def get_data_file(basename):
    return (Path(__file__) / '../data' / basename).resolve()


def make_tag_dict(nlmaps_file=None):
    most_common_tags = read_tags(get_data_file('most_common_tags.json'))
    open_keys = read_keys(get_data_file('open_keys.txt'))
    dropped_keys = read_keys(get_data_file('dropped_keys.txt'))
    with open(get_data_file('additional_tags.json')) as f:
        additional_tags = json.load(f)

    tag_dict = most_common_tags

    special_phrases_file = get_data_file('special_phrases.txt')
    special_phrases_tags = [
        tuple(tag.split('='))
        for tag in get_special_phrases_tags(special_phrases_file)
    ]
    for key, value in special_phrases_tags:
        if key in tag_dict:
            tag_dict[key].add(value)
        else:
            tag_dict[key] = {value}

    if nlmaps_file:
        nlmaps_dataset_tags = get_tags_from_nlmaps_dataset(nlmaps_file)

    for key, value in nlmaps_dataset_tags:
        if key in tag_dict:
            tag_dict[key].add(value)
        else:
            tag_dict[key] = {value}

    for key, values in additional_tags.items():
        if key in tag_dict:
            tag_dict[key].update(values)
        else:
            tag_dict[key] = set(values)

    for key in open_keys:
        tag_dict[key] = None

    for key in dropped_keys:
        if key in tag_dict:
            del tag_dict[key]

    return tag_dict


def main(nlmaps_file=None, pickle_outfile=None):
    tag_dict = make_tag_dict(nlmaps_file)
    for key, values in tag_dict.items():
        if values:
            print('{}: {}'.format(key, ', '.join(values)))
        else:
            print('{}: None'.format(key))

    if pickle_outfile:
        with open(pickle_outfile, 'wb') as f:
            pickle.dump(tag_dict, f)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nlmaps-file',
                        help='NLMaps dataset file to load tags from')
    parser.add_argument('--pickle-outfile',
                        help='Pickle file to save tag dict in')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    ARGS = parse_args()
    main(**vars(ARGS))
