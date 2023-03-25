from typing import Any, Protocol
from pydantic import BaseModel, validator


class ProcessingError(Exception):
    pass


class Processor(Protocol):
    sources: frozenset[str]
    target: str
    name: str

    def __call__(self, given: dict[str, Any]) -> str:
        ...

    def __eq__(self, other: Any) -> str:
        ...

    def __hash__(self) -> int:
        ...


class ProcessingRequest(BaseModel):
    given: dict[str, Any]
    wanted: set[str]
    processors: set[str]

    @validator("wanted", "processors", pre=True)
    def convert_list_to_set(cls, v) -> set:
        if isinstance(v, set):
            return v

        assert isinstance(v, list), f"Value must be a list, but is of type {type(v)}"
        v_set = set(v)
        assert len(v_set) == len(v), "Elements may only occur once"
        return v_set


class SingleProcessorResult(BaseModel):
    result: Any
    processor_name: str
    wallclock_seconds: float


class ProcessingResult(BaseModel):
    results: dict[str, SingleProcessorResult]
    wallclock_seconds: float
