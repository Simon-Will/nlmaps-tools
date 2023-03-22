from typing import Optional, Union, Any

from OSMPythonTools.element import Element
from geopy.distance import geodesic
from pydantic import BaseModel

from OSMPythonTools.overpass import OverpassResult

from nlmaps_tools.answer_mrl import (
    OVERPASS,
    chop_to_cardinal_direction,
    handle_around_topx,
    element_name,
    geojson, latlong
)
from nlmaps_tools.features_to_overpass import Will2021FeaturesAfterNwrNameLookup, OSMArea
from nlmaps_tools.parse_mrl import Symbol

GeoJSON = dict[str, Any]


class SingleAnswer(BaseModel):
    type: str


class MapAnswer(SingleAnswer):
    type = "map"


class TextAnswer(SingleAnswer):
    type = "text"
    text: str


class ListAnswer(SingleAnswer):
    type = "list"
    list: list[str]


class DistAnswer(SingleAnswer):
    type = "dist"
    dist: float
    target: tuple[int, str]  # ID and name
    center: tuple[int, str]  # ID and name


class MultiAnswerRawElements(BaseModel):
    answers: list[SingleAnswer]
    targets: list[Element]
    centers: Optional[list[Element]]

    class Config:
        arbitrary_types_allowed = True


class MultiAnswer(BaseModel):
    answers: list[SingleAnswer]
    targets: GeoJSON
    centers: Optional[GeoJSON]


def query_overpass(overpass_ql) -> OverpassResult:
    result = OVERPASS.query(overpass_ql)
    return result


def apply_qtype(qtype, elements):
    if qtype == Symbol('latlong'):
        return MapAnswer()
    elif qtype == ('least', ('topx', Symbol('1'))):
        text = 'Yes' if len(elements) > 0 else 'No'
        return TextAnswer(text=text)
    elif qtype == Symbol('count'):
        return TextAnswer(text=str(len(elements)))
    elif isinstance(qtype, tuple) and qtype[0] == 'findkey':
        # TODO: Handle multiple keys
        key = qtype[1]
        name = lambda elm: ('{} {}'.format(elm.type(), elm.id())
                            if key == 'name' else element_name(elm))
        values = ['{}: {}'.format(name(elm), str(elm.tag(key)))
                  for elm in elements]
        return ListAnswer(list=values)
    raise ValueError(f'Unknown qtype: {qtype}')


def extract_answer_from_simple_overpass_result(
    features: Will2021FeaturesAfterNwrNameLookup,
    area: Optional[OSMArea],
    result: OverpassResult,
) -> MultiAnswerRawElements:
    elements = result.elements()

    if (features['query_type'] == 'in_query'
            and features.get('cardinal_direction')
            and area):
        card = features['cardinal_direction']
        bbox = [float(coord) for coord in area['boundingbox']]
        elements = chop_to_cardinal_direction(elements, bbox, card)

    if features['query_type'] == 'around_query':
        centers, targets, target_id_min_dist = handle_around_topx(elements, features)
    else:
        centers = []
        targets = elements

    answer = MultiAnswerRawElements(answers=[], targets=targets)
    if centers:
        answer.centers = centers
    if features['query_type'] == 'around_query' and features["query_type"] == "dist":
        targets_by_id = {target.id(): target for target in targets}
        for center, (target_id, min_dist) in zip(centers, target_id_min_dist):
            if target_id:
                answer.answers.append(
                    DistAnswer(
                        dist=min_dist,
                        target=(target_id, element_name(targets_by_id[target_id])),
                        center=(center.id(), element_name(center)),
                    )
                )
    else:
        answer.answers = [apply_qtype(qtype, targets) for qtype in features['qtype']]

    return answer


def extract_answer_from_dist_overpass_result(
    features: Will2021FeaturesAfterNwrNameLookup,
    area_1: Optional[OSMArea],
    area_2: Optional[OSMArea],
    result_1: OverpassResult,
    result_2: OverpassResult,
) -> MultiAnswerRawElements:
    answer_1 = extract_answer_from_simple_overpass_result(features["sub"][0], area_1, result_1)
    answer_2 = extract_answer_from_simple_overpass_result(features["sub"][1], area_2, result_2)

    center = answer_1.targets[0] if answer_1.targets else None
    target = answer_2.targets[0] if answer_2.targets else None
    dist = geodesic(latlong(center), latlong(target)).kilometers

    if center and target:
        return MultiAnswerRawElements(
            answers=[
                DistAnswer(
                    dist=dist,
                    target=(target.id(), element_name(target)),
                    center=(center.id(), element_name(center)),
                )
            ],
            targets=[target],
            centers=[center],
        )

    if center:
        error =  'No result for query 2.'
    elif target:
        error =  'No result for query 1.'
    else:
        error =  'No result, neither for query 1 nor for query 2.'
    raise ValueError(error)


def extract_answer_from_overpass_results(
    features: Will2021FeaturesAfterNwrNameLookup,
    areas: list[Optional[OSMArea]],
    results: list[OverpassResult],
) -> MultiAnswer:
    assert len(areas) == len(results)
    if len(results) == 1:
        answer = extract_answer_from_simple_overpass_result(features, areas[0], results[0])
    elif len(results) == 2:
        answer = extract_answer_from_dist_overpass_result(
            features, areas[0], areas[1], results[0], results[1]
        )
    else:
        raise ValueError(
            f"The list of results must contain one or two results, but contains {len(results)}."
        )
    return MultiAnswer(
        answers=answer.answers,
        targets=geojson(answer.targets),
        centers=geojson(answer.centers) if answer.centers else None,
    )