from copy import deepcopy
import logging
from typing import Optional, Any, Iterator

from OSMPythonTools.nominatim import NominatimResult

from nlmaps_tools.answer_mrl import (
    add_name_tags,
    canonicalize_nwr_features,
    transform_features,
    nominatim_query,
    ENV,
    nwr_nominatim_lookup,
)

Will2021RawFeatures = dict
Will2021CanonicalFeatures = dict
Will2021FeaturesAfterAreaLookup = dict
Will2021FeaturesAfterNwrNameLookup = dict
OverpassQuery = str


class OSMArea:
    def __init__(self, dct: dict, id: int) -> None:
        self.id = id
        self._dct = dct

    def __getitem__(self, key: str) -> Any:
        return self._dct[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._dct[key] = value

    def __delitem__(self, key: str):
        del self._dct[key]

    def __iter__(self) -> Iterator:
        return iter(self._dct)

    def __len__(self) -> int:
        return len(self._dct)

    def __repr__(self) -> str:
        return f"OSMArea(id={self.id!r}, _dct={self._dct!r})"


def get_first_area(nominatim_result: NominatimResult) -> Optional[OSMArea]:
    for d in nominatim_result._json:
        if "osm_type" in d and d["osm_type"] in ["relation", "way"] and "osm_id" in d:
            magic_number = 3600000000 if d["osm_type"] == "relation" else 2400000000
            area_id = magic_number + int(d["osm_id"])
            area = OSMArea(dct=d, id=area_id)
            return area
    return None


def nominatim_find_area(features: Will2021CanonicalFeatures) -> Optional[OSMArea]:
    area_name = features.get("area")
    if area_name:
        n_result = nominatim_query(area_name)
        area = get_first_area(n_result)
        if area:
            logging.info(
                "Nominatim query for area {!r} yielded area ID {}.".format(
                    area_name, area.id
                )
            )
            return area
        logging.warning(
            "Nominatim query for area {!r} did not yield an area.".format(area_name)
        )
    return None


def canonicalize_features(features: Will2021RawFeatures) -> Will2021CanonicalFeatures:
    features = transform_features(features, add_name_tags)
    features = transform_features(features, canonicalize_nwr_features)
    return features


def render_simple_overpass_query(
    features: Will2021FeaturesAfterNwrNameLookup,
) -> OverpassQuery:
    template_name = features["query_type"] + ".jinja2"
    template = ENV.get_template(template_name)
    ql = template.render(features=features)
    return ql


def nominatim_replace_names_in_nwrs(
    features: Will2021FeaturesAfterAreaLookup, area: Optional[OSMArea]
) -> Will2021FeaturesAfterNwrNameLookup:
    if area:
        bbox = area["boundingbox"]
        # from (minlat, maxlat, minlon, maxlon)
        # to (minlon, minlat, maxlon, maxlat)
        bbox = (bbox[2], bbox[0], bbox[3], bbox[1])
    else:
        bbox = None

    features = deepcopy(features)

    center_nwr = features.get("center_nwr")
    target_nwr = features.get("target_nwr")
    if center_nwr:
        new_center_nwr, _ = nwr_nominatim_lookup(center_nwr, bbox=bbox)
        if new_center_nwr:
            features["center_nwr"] = new_center_nwr
    elif target_nwr:
        new_target_nwr, _ = nwr_nominatim_lookup(target_nwr, bbox=bbox)
        if new_target_nwr:
            features["target_nwr"] = new_target_nwr

    return features


def add_area_id(
    features: Will2021CanonicalFeatures, area: Optional[OSMArea]
) -> Will2021FeaturesAfterAreaLookup:
    if area:
        features["area_id"] = area.id
    return features


def make_overpass_query_from_simple_features(
    features: Will2021RawFeatures,
) -> tuple[Will2021FeaturesAfterNwrNameLookup, Optional[OSMArea], OverpassQuery]:
    features = canonicalize_features(features)
    logging.info(f"Canonicalized features to {features}.")

    area = nominatim_find_area(features)
    features = add_area_id(features, area)
    logging.info(f"Retrieved area {area}.")

    features = nominatim_replace_names_in_nwrs(features, area)

    logging.info(f"Replaced names in nwr operators, resulting in {features}.")
    overpass_query = render_simple_overpass_query(features)

    return features, area, overpass_query


def make_overpass_queries_from_features(
    features: Will2021RawFeatures,
) -> tuple[
    Will2021FeaturesAfterNwrNameLookup, list[Optional[OSMArea]], list[OverpassQuery]
]:
    if features["query_type"] in ["around_query", "in_query"]:
        features, area, overpass_query = make_overpass_query_from_simple_features(
            features
        )
        return features, [area], [overpass_query]

    if features["query_type"] == "dist" and len(features["sub"]) == 1:
        sub_features, area, overpass_query = make_overpass_query_from_simple_features(
            features["sub"][0]
        )
        features["sub"][0] = sub_features
        return features, [area], [overpass_query]

    if features["query_type"] == "dist" and len(features["sub"]) == 2:
        sub_features_0, area_0, overpass_query_0 = make_overpass_query_from_simple_features(
            features["sub"][0]
        )
        sub_features_1, area_1, overpass_query_1 = make_overpass_query_from_simple_features(
            features["sub"][1]
        )
        features["sub"][0] = sub_features_0
        features["sub"][1] = sub_features_1
        return features, [area_0, area_1], [overpass_query_0, overpass_query_1]

    raise ValueError(f'Unsupported query_type {features["query_type"]}')
