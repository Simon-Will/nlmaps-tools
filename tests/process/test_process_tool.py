from collections.abc import Collection
from typing import Any
import logging

import pytest

from nlmaps_tools.process import (
    ProcessRequest,
    ProcessResult,
    ProcessTool,
)
from nlmaps_tools.process.processors import BuiltinProcessor


class DummyProcessor(BuiltinProcessor):
    def __init__(self, sources: Collection[str], target: str) -> None:
        name = f"{'/'.join(sources)}-{target}"
        super().__init__(sources=sources, target=target, name=name)

    def __call__(self, given: dict[str, Any]) -> str:
        formatted_args = ",".join(given[source] for source in self.sources)
        result = f"{self.name}({formatted_args})"
        logging.info(f"{self.name}: {formatted_args} -> {result}")
        return result

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


@pytest.fixture
def processors() -> set[DummyProcessor]:
    return {
        DummyProcessor(["A"], "B"),
        DummyProcessor(["B"], "A"),
        DummyProcessor(["B"], "E"),
        DummyProcessor(["B"], "C"),
        DummyProcessor(["B"], "D"),
        DummyProcessor(["B", "C", "D"], "E"),
        DummyProcessor(["E"], "G"),
        DummyProcessor(["A", "F"], "B"),
    }


@pytest.fixture
def process_tool(processors) -> ProcessTool:
    return ProcessTool(processors)


def _get_processors_by_name(
        processors: set[DummyProcessor], names: set[str]
) -> set[DummyProcessor]:
    return {proc for proc in processors if proc.name in names}


@pytest.mark.parametrize(
    ["process_request", "expected_solutions_by_names"],
    [
        (
                ProcessRequest(given={"A": "1"}, wanted={"E"}, processors=set()),
                [{"A-B", "B-E"}, {"A-B", "B-C", "B-D", "B/C/D-E"}],
        ),
        (
                ProcessRequest(given={"A": "1", "F": "2"}, wanted={"E"}, processors=set()),
                [
                    {"A-B", "B-E"},
                    {"A-B", "B-C", "B-D", "B/C/D-E"},
                    {"A/F-B", "B-E"},
                    {"A/F-B", "B-C", "B-D", "B/C/D-E"},
                ],
        ),
        (
                ProcessRequest(given={"A": "1"}, wanted={"E", "B", "G"}, processors=set()),
                [{"A-B", "B-E", "E-G"}, {"A-B", "B-C", "B-D", "B/C/D-E", "E-G"}],
        ),
        (
                ProcessRequest(given={"A": "1"}, wanted={"E", "C"}, processors=set()),
                [{"A-B", "B-C", "B-E"}, {"A-B", "B-C", "B-D", "B/C/D-E"}],
        ),
    ],
)
def test_find_solutions(process_tool, process_request, expected_solutions_by_names):
    expected_frozen_solutions = frozenset(
        frozenset(_get_processors_by_name(process_tool.processors, names))
        for names in expected_solutions_by_names
    )
    solutions = process_tool._find_solutions(process_request)
    frozen_solutions = frozenset(frozenset(s) for s in solutions)
    assert frozen_solutions == expected_frozen_solutions


def test_process_request(process_tool):
    request = ProcessRequest(given={"A": "1"}, wanted={"B"}, processors=set())
    expected_result = ProcessResult(results={"B": "A-B(1)"})
    result = process_tool.process_request(request)
    assert result == expected_result
