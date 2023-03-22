from abc import ABC
from typing import Any, Optional

from OSMPythonTools.overpass import OverpassResult

from nlmaps_tools.mrl import NLmaps
from nlmaps_tools.parse_mrl import MrlGrammar

from .models import ProcessingError
from nlmaps_tools.features_to_overpass import OverpassQuery, make_overpass_queries_from_features, \
    FeaturesAfterNwrNameLookup, OSMArea
from ..answer_mrl import OVERPASS
from ..answer_overpass import MultiAnswer, extract_answer_from_overpass_results


class BuiltinProcessor(ABC):
    def __eq__(self, other: Any) -> str:
        return (
            type(self) == type(other)
            and self.name == other.name
            and self.sources == other.sources
            and self.target == other.target
        )

    def __hash__(self) -> int:
        return hash((self.sources, self.target, self.name))

    def __repr__(self) -> str:
        return self.name


class Functionalizer(BuiltinProcessor):
    def __init__(self, source: str, target: str) -> None:
        self.mrl_world = NLmaps()
        self.source = source
        self.target = target

        self.sources = frozenset([source])
        self.name = f"Functionalize_{source}_{target}"

    def __call__(self, given: dict[str, Any]) -> str:
        linear_mrl = given[self.source]
        try:
            return self.mrl_world.functionalise(linear_mrl)
        except Exception as e:
            raise ProcessingError(f"Could not linearize {linear_mrl}") from e


class Linearizer(BuiltinProcessor):
    def __init__(self, source: str, target: str) -> None:
        self.mrl_world = NLmaps()
        self.source = source
        self.target = target

        self.sources = frozenset([source])
        self.name = f"Linearize_{source}_{target}"

    def __call__(self, given: dict[str, Any]) -> str:
        functional_mrl = given[self.source]
        try:
            return self.mrl_world.preprocess_mrl(functional_mrl)
        except Exception as e:
            raise ProcessingError(f"Could not functionalize {functional_mrl}") from e


class Will2021FeatureExtractor(BuiltinProcessor):
    def __init__(self):
        self.source = "Will2021"
        self.sources = frozenset([self.source])
        self.target = "Will2021Features"
        self.name = "ExtractFeatures_Will2021"

        self.grammar = MrlGrammar()

    def __call__(self, given: dict[str, Any]) -> dict:
        will2021 = given[self.source]
        parse_result = self.grammar.parseMrl(will2021, is_escaped=False)
        features = parse_result["features"]

        # TODO: Put this into nlmaps-tools.
        if features["query_type"] == "dist":
            if len(features["sub"]) == 1:
                features["query_type"] = "dist_closest"
            else:
                features["query_type"] = "dist_between"

        return features


class OverpassQueryConstructor(BuiltinProcessor):
    def __init__(self):
        self.source = "Will2021Features"
        self.sources = frozenset([self.source])
        self.target = "_Will2021PostFeaturesAreasOverpassQueries"
        self.name = "ConstructOverpassQueries_Will2021"

    def __call__(
        self, given: dict[str, Any]
    ) -> tuple[FeaturesAfterNwrNameLookup, list[Optional[OSMArea]], list[OverpassQuery]]:
        features = given[self.source]
        return make_overpass_queries_from_features(features)


class Will2021PostFeaturesExtractor(BuiltinProcessor):
    def __init__(self):
        self.source = "_Will2021PostFeaturesAreasOverpassQueries"
        self.sources = frozenset([self.source])
        self.target = "Will2021PostFeatures"
        self.name = "ExtractWill2021PostFeatures"

    def __call__(self, given: dict[str, Any]) -> FeaturesAfterNwrNameLookup:
        triple = given[self.source]
        return triple[0]


class OSMAreasExtractor(BuiltinProcessor):
    def __init__(self):
        self.source = "_Will2021PostFeaturesAreasOverpassQueries"
        self.sources = frozenset([self.source])
        self.target = "MaybeOSMAreas"
        self.name = "ExtractOSMAreas"

    def __call__(self, given: dict[str, Any]) -> list[Optional[OSMArea]]:
        triple = given[self.source]
        return triple[1]


class OverpassQueriesExtractor(BuiltinProcessor):
    def __init__(self):
        self.source = "_Will2021PostFeaturesAreasOverpassQueries"
        self.sources = frozenset([self.source])
        self.target = "OverpassQueryList"
        self.name = "ExtractOverpassQueryList"

    def __call__(self, given: dict[str, Any]) -> list[OverpassQuery]:
        triple = given[self.source]
        return triple[2]


class OverpassQueriesExecutor(BuiltinProcessor):
    def __init__(self):
        self.source = "OverpassQueryList"
        self.sources = frozenset([self.source])
        self.target = "OverpassResultList"
        self.name = "ExecuteOverpassQueries_Will2021"

    def __call__(self, given: dict[str, Any]) -> list[OverpassResult]:
        queries = given[self.source]
        results = [OVERPASS.query(query) for query in queries]
        return results


class OverpassAnswerExtractor(BuiltinProcessor):
    def __init__(self):
        self.sources = frozenset([
            "Will2021PostFeatures", "OverpassResultList", "MaybeOSMAreas"
        ])
        self.target= "Will2021MultiAnswer"
        self.name = "ExtractAnswer_Will2021"

    def __call__(self, given: dict[str, Any]) -> MultiAnswer:
        features = given["Will2021PostFeatures"]
        areas = given["MaybeOSMAreas"]
        results = given["OverpassResultList"]
        multi_answer = extract_answer_from_overpass_results(
            features=features,
            areas=areas,
            results=results
        )
        return multi_answer


PROCESSORS = [
    # Functionalizer("Lawrence2018Lin", "Lawrence2018"),
    # Linearizer("Lawrence2018", "Lawrence2018Lin"),
    Functionalizer("Will2021Lin", "Will2021"),
    # Linearizer("Will2021", "Will2021Lin"),
    Will2021FeatureExtractor(),
    OverpassQueryConstructor(),
    Will2021PostFeaturesExtractor(),
    OSMAreasExtractor(),
    OverpassQueriesExtractor(),
    OverpassQueriesExecutor(),
    OverpassAnswerExtractor(),
]