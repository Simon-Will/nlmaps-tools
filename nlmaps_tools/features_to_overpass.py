import argparse
import json
import logging
import sys

from nlmaps_tools.parse_mrl import MrlGrammar, Symbol
from nlmaps_tools.answer_mrl import (
    add_name_tags,
    canonicalize_nwr_features,
    load_features,
    transform_features,
)


def render_overpass(features):
    if features:
        print(features)
        features = transform_features(features, add_name_tags)
        features = transform_features(features, canonicalize_nwr_features)
        print(features)

        try:
            if features["query_type"] in ["around_query", "in_query"]:
                ans, _, _ = answer_simple_query(features)
                return ans
            elif features["query_type"] == "dist" and len(features["sub"]) == 1:
                ans, _, _ = answer_simple_query(features)
                return ans
            elif features["query_type"] == "dist" and len(features["sub"]) == 2:
                ans, _, _ = answer_dist_between_query(features)
                return ans
            else:
                error = "query_type {} not supported yet".format(features["query_type"])
        except Exception as exc:
            if len(exc.args) > 0:
                error = exc.args[0]
            else:
                error = "Unknown MRL interpretation error"
    else:
        error = "No features given"

    return {"type": "error", "error": error}


def main(mrl, escaped=False):
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
    )
    features = load_features(mrl, escaped=escaped)
    logging.info(features)
    overpass = render_overpass(features)
    logging.info(overpass)


def parse_args():
    parser = argparse.ArgumentParser(description="Answer an MRL")
    parser.add_argument("mrl", help="MRL as string or MRL features as json string")
    parser.add_argument(
        "--escaped",
        action="store_true",
        default=False,
        help="Whether the mrl is in escaped form. Default: False",
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    ARGS = parse_args()
    main(**vars(ARGS))
