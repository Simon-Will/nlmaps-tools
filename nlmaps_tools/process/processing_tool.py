from collections import defaultdict
import logging
import time
from typing import Iterable, Union, Any

from .models import Processor, ProcessingRequest, ProcessingResult, SingleProcessorResult


class SolutionFindingError(Exception):
    pass


def _find_solutions(
    wanted: Union[set[str], frozenset[str]],
    having: set[str],
    target_to_processors: dict[str, set[Processor]],
    targets_causing_cycles: set[str] = frozenset(),
    depth: int = 0,
) -> list[set[Processor]]:
    p = (str(depth) + " " * (2 * depth - 1)) if depth else ""
    solutions = [set()]
    logging.debug(f"{p}Looking for {wanted} from {having}")
    for target in wanted:
        logging.debug(f"{p}Checking for target {target}")
        new_solutions = []
        for solution in solutions:
            solution_having = having | {proc.target for proc in solution}
            logging.debug(
                f"{p}Checking for solution {solution} having {solution_having}"
            )
            if target in solution_having:
                new_solutions.append(solution)
                continue

            for proc in target_to_processors.get(target, []):
                logging.debug(f"{p}Checking for proc {proc}")
                if proc.sources.intersection(targets_causing_cycles):
                    # Using this processor would create a cycle.
                    logging.debug(
                        f"{p}Detected cycle if using proc {proc}."
                        f" Targets causing cycles: {targets_causing_cycles}"
                    )
                    continue

                if proc.sources.issubset(solution_having):
                    subsequent_partial_solutions = [set()]
                else:
                    subsequent_partial_solutions = _find_solutions(
                        wanted=proc.sources,
                        having=solution_having | {target},
                        # Disallow revisiting of a target by removing entry from target_to_processors.
                        target_to_processors={
                            t: p for t, p in target_to_processors.items() if t != target
                        },
                        targets_causing_cycles=targets_causing_cycles | {target},
                        depth=depth + 1,
                    )

                for sub_solution in subsequent_partial_solutions:
                    logging.debug(f"{p}Appending {[proc]} and {sub_solution}")
                    new_solutions.append(solution | {proc} | sub_solution)

        logging.debug(f"{p}New solutions: {new_solutions}")
        solutions = new_solutions
    logging.debug(f"{p}Returning {solutions}")
    return solutions


def _build_target_to_processors(
    processors: Iterable[Processor],
) -> dict[str, set[Processor]]:
    target_to_processors = defaultdict(set)
    for p in processors:
        target_to_processors[p.target].add(p)
    return target_to_processors


class ProcessingTool:
    def __init__(self, processors: set[Processor]) -> None:
        self.processors = processors
        self.target_to_processors = _build_target_to_processors(self.processors)

    def find_processor_chain(self, request: ProcessingRequest) -> list[Processor]:
        solutions = self._find_solutions(request)
        solution = self._choose_solution(solutions)
        processor_chain = self._order_solution(set(request.given), solution)
        return processor_chain

    def process_request(self, request: ProcessingRequest) -> ProcessingResult:
        processor_chain = self.find_processor_chain(request)
        result = self._apply_processor_chain(request.given, processor_chain)
        return result

    @staticmethod
    def select_wanted_from_result(
        result: ProcessingResult, request: ProcessingRequest
    ) -> ProcessingResult:
        wanted_results = {key: val for key, val in result.results.items() if key in request.wanted}
        return ProcessingResult(results=wanted_results, wallclock_seconds=result.wallclock_seconds)

    def _find_solutions(self, request: ProcessingRequest) -> list[set[Processor]]:
        solutions = _find_solutions(
            wanted=request.wanted,
            having=set(request.given),
            target_to_processors=self.target_to_processors,
        )
        return solutions

    @staticmethod
    def _choose_solution(solutions: list[set[Processor]]) -> set[Processor]:
        # This choice is pretty random and should be improved.
        # Ideas:
        #  - Choose solutions with fewer processors.
        #  - Attach penalties to processors and choose based on least penalty
        return solutions[0]

    @staticmethod
    def _order_solution(given: set[str], processors: set[Processor]) -> list[Processor]:
        chain = []
        having = given.copy()
        processors = processors.copy()
        while processors:
            for proc in processors:
                if proc.sources.issubset(having):
                    chain.append(proc)
                    having.add(proc.target)
                    processors.remove(proc)
                    break
            else:
                raise SolutionFindingError(
                    f"Could not build chain from processors {processors!r} given {given!r}."
                )
        return chain

    @staticmethod
    def _apply_processor_chain(
        given: dict[str, Any], processor_chain: list[Processor]
    ) -> ProcessingResult:
        total_start = time.perf_counter()
        logging.info(f"Applying processor chain {' -> '.join(str(p) for p in processor_chain)}.")
        results = {}
        for proc in processor_chain:
            logging.info(f"Applying processor {proc}.")
            start = time.perf_counter()
            given[proc.target] = proc(
                {key: val for key, val in given.items() if key in proc.sources}
            )
            results[proc.target] = SingleProcessorResult(
                result=given[proc.target],
                processor_name=proc.name,
                wallclock_seconds=time.perf_counter() - start
            )
        return ProcessingResult(results=results, wallclock_seconds=time.perf_counter() - total_start)
