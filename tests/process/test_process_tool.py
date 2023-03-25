from collections.abc import Collection
from typing import Any
import logging

import pytest

from nlmaps_tools.process import (
    ProcessingRequest,
    ProcessingResult,
    ProcessingTool,
)
from nlmaps_tools.process.models import SingleProcessorResult
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
def process_tool(processors) -> ProcessingTool:
    return ProcessingTool(processors)


def _get_processors_by_name(
        processors: set[DummyProcessor], names: set[str]
) -> set[DummyProcessor]:
    return {proc for proc in processors if proc.name in names}


@pytest.mark.parametrize(
    ["process_request", "expected_solutions_by_names"],
    [
        (
                ProcessingRequest(given={"A": "1"}, wanted={"E"}, processors=set()),
                [{"A-B", "B-E"}, {"A-B", "B-C", "B-D", "B/C/D-E"}],
        ),
        (
                ProcessingRequest(given={"A": "1", "F": "2"}, wanted={"E"}, processors=set()),
                [
                    {"A-B", "B-E"},
                    {"A-B", "B-C", "B-D", "B/C/D-E"},
                    {"A/F-B", "B-E"},
                    {"A/F-B", "B-C", "B-D", "B/C/D-E"},
                ],
        ),
        (
                ProcessingRequest(given={"A": "1"}, wanted={"E", "B", "G"}, processors=set()),
                [{"A-B", "B-E", "E-G"}, {"A-B", "B-C", "B-D", "B/C/D-E", "E-G"}],
        ),
        (
                ProcessingRequest(given={"A": "1"}, wanted={"E", "C"}, processors=set()),
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
    request = ProcessingRequest(given={"A": "1"}, wanted={"B"}, processors=set())
    expected_result_key = "B"
    expected_result_value = "A-B(1)"
    expected_result_processor_name = "A-B"
    max_result_time = 0.01  # Pretty randomly chosen.
    result = process_tool.process_request(request)
    assert list(result.results.keys()) == [expected_result_key]
    assert result.results[expected_result_key].result == expected_result_value
    assert result.results[expected_result_key].processor_name == expected_result_processor_name
    assert result.results[expected_result_key].wallclock_seconds < max_result_time
    assert result.wallclock_seconds > result.results[expected_result_key].wallclock_seconds


def test_select_wanted_from_result(process_tool):
    request = ProcessingRequest(given={"A": "1"}, wanted={"C"}, processors=set())
    given_result = ProcessingResult(
        results={
            "B": SingleProcessorResult(result="A-B(1)", processor_name="A-B", wallclock_seconds=0.05),
            "C": SingleProcessorResult(result="B-C(A-B(1))", processor_name="B-C", wallclock_seconds=0.05),
        },
        wallclock_seconds=0.11
    )
    expected_result = ProcessingResult(
        results={
            "C": SingleProcessorResult(result="B-C(A-B(1))", processor_name="B-C", wallclock_seconds=0.05),
        },
        wallclock_seconds=0.11
    )
    selected_result = process_tool.select_wanted_from_result(given_result, request)
    assert selected_result == expected_result
