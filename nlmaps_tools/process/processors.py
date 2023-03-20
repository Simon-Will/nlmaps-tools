from abc import ABC
from typing import Any, Optional, Iterable

from OSMPythonTools.overpass import OverpassResult

from nlmaps_tools.answer_mrl import OVERPASS
from nlmaps_tools.answer_overpass import MultiAnswer, extract_answer_from_overpass_results
from nlmaps_tools.features_to_overpass import (
    make_overpass_queries_from_features,
    OSMArea,
    OverpassQuery,
    Will2021FeaturesAfterNwrNameLookup,
)
from nlmaps_tools.mrl import NLmaps
from nlmaps_tools.parse_mrl import MrlGrammar

from .models import ProcessingError


class BuiltinProcessor(ABC):
    def __init__(
        self,
        sources: Iterable[str],
        target: str,
        name: Optional[str] = None
    ) -> None:
        self.sources = frozenset(sources)
        self.target = target

        if name:
            self.name = name
        else:
            sources_str = "/".join(self.sources)
            self.name = f"{self.__class__.__name__}-{sources_str}-{target}"

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
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"sources={self.sources!r}, "
            f"target={self.target!r}"
            ")"
        )

    def __str__(self) -> str:
        return self.name


class Functionalizer(BuiltinProcessor):
    def __init__(self, source: str, target: str) -> None:
        self.mrl_world = NLmaps()
        self.source = source
        super().__init__(sources=[source], target=target)

    def __call__(self, given: dict[str, Any]) -> str:
        linear_mrl = given[self.source]
        try:
            return self.mrl_world.functionalise(linear_mrl)
        except Exception as e:
            raise ProcessingError(f"Could not linearize {linear_mrl!r}") from e


class Linearizer(BuiltinProcessor):
    def __init__(self, source: str, target: str) -> None:
        self.mrl_world = NLmaps()
        self.source = source
        super().__init__(sources=[source], target=target)

    def __call__(self, given: dict[str, Any]) -> str:
        functional_mrl = given[self.source]
        try:
            return self.mrl_world.preprocess_mrl(functional_mrl)
        except Exception as e:
            raise ProcessingError(f"Could not functionalize {functional_mrl!r}") from e


class Will2021FeatureExtractor(BuiltinProcessor):
    def __init__(self):
        self.source = "Will2021MRL"
        self.grammar = MrlGrammar()
        target = "Will2021Features"
        super().__init__(sources=[self.source], target=target)

    def __call__(self, given: dict[str, Any]) -> dict:
        will2021 = given[self.source]
        parse_result = self.grammar.parseMrl(will2021, is_escaped=False)
        features = parse_result["features"]
        return features


class OverpassQueryConstructor(BuiltinProcessor):
    def __init__(self):
        self.source = "Will2021Features"
        target = "_Will2021FeaturesAfterNwrNameLookup_OSMAreaList_OverpassQueryList"
        super().__init__(sources=[self.source], target=target)

    def __call__(
        self, given: dict[str, Any]
    ) -> tuple[Will2021FeaturesAfterNwrNameLookup, list[Optional[OSMArea]], list[OverpassQuery]]:
        features = given[self.source]
        return make_overpass_queries_from_features(features)


class Will2021PostFeaturesExtractor(BuiltinProcessor):
    def __init__(self):
        self.source = "_Will2021FeaturesAfterNwrNameLookup_OSMAreaList_OverpassQueryList"
        target = "Will2021FeaturesAfterNwrNameLookup"
        super().__init__(sources=[self.source], target=target)

    def __call__(self, given: dict[str, Any]) -> Will2021FeaturesAfterNwrNameLookup:
        triple = given[self.source]
        return triple[0]


class OSMAreasExtractor(BuiltinProcessor):
    def __init__(self):
        self.source = "_Will2021FeaturesAfterNwrNameLookup_OSMAreaList_OverpassQueryList"
        target = "OSMAreaList"
        super().__init__(sources=[self.source], target=target)

    def __call__(self, given: dict[str, Any]) -> list[Optional[OSMArea]]:
        triple = given[self.source]
        return triple[1]


class OverpassQueriesExtractor(BuiltinProcessor):
    def __init__(self):
        self.source = "_Will2021FeaturesAfterNwrNameLookup_OSMAreaList_OverpassQueryList"
        target = "OverpassQueryList"
        super().__init__(sources=[self.source], target=target)

    def __call__(self, given: dict[str, Any]) -> list[OverpassQuery]:
        triple = given[self.source]
        return triple[2]


class OverpassQueriesExecutor(BuiltinProcessor):
    def __init__(self):
        self.source = "OverpassQueryList"
        target = "OverpassResultList"
        super().__init__(sources=[self.source], target=target)

    def __call__(self, given: dict[str, Any]) -> list[OverpassResult]:
        queries = given[self.source]
        results = [OVERPASS.query(query) for query in queries]
        return results


class OverpassAnswerExtractor(BuiltinProcessor):
    def __init__(self):
        sources = [
            "Will2021FeaturesAfterNwrNameLookup", "OSMAreaList", "OverpassResultList"
        ]
        target= "Will2021MultiAnswer"
        super().__init__(sources=sources, target=target)

    def __call__(self, given: dict[str, Any]) -> MultiAnswer:
        features = given["Will2021FeaturesAfterNwrNameLookup"]
        areas = given["OSMAreaList"]
        results = given["OverpassResultList"]
        multi_answer = extract_answer_from_overpass_results(
            features=features,
            areas=areas,
            results=results
        )
        return multi_answer


PROCESSORS = [
    Functionalizer("Lawrence2018Lin", "Lawrence2018MRL"),
    Linearizer("Lawrence2018MRL", "Lawrence2018Lin"),
    Functionalizer("Will2021Lin", "Will2021MRL"),
    Linearizer("Will2021MRL", "Will2021Lin"),
    Will2021FeatureExtractor(),
    OverpassQueryConstructor(),
    Will2021PostFeaturesExtractor(),
    OSMAreasExtractor(),
    OverpassQueriesExtractor(),
    OverpassQueriesExecutor(),
    OverpassAnswerExtractor(),
]