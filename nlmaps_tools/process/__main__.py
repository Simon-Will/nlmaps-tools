import argparse
import logging
import sys

from nlmaps_tools.process import ProcessingTool, ProcessingRequest
from nlmaps_tools.process.processors import PROCESSORS


def main(given: list[tuple[str, str]], wanted: list[str], verbose=False):
    logging.basicConfig(
        level=logging.INFO if verbose else logging.ERROR,
        stream=sys.stdout,
    )
    processing_tool = ProcessingTool(PROCESSORS)
    request = ProcessingRequest(given=dict(given), wanted=set(wanted), processors=set())
    result = processing_tool.process_request(request)
    output = "\n\n".join(f"{form}: {value}" for form, value in result.results.items())
    print(output)


def parse_given(given: str) -> tuple[str, str]:
    parts = given.split("=", maxsplit=1)
    assert len(parts) == 2
    return tuple(parts)


def parse_args():
    available_sources = sorted(
        {source for processor in PROCESSORS for source in processor.sources}
    )
    available_targets = sorted({processor.target for processor in PROCESSORS})

    parser = argparse.ArgumentParser(
        description=(
            "Process some sources into a target using the processors provided by nlmaps-tools."
            " Example:\n"
            '  python -m nlmaps_tools.process --wanted MultiAnswer --wanted Will2021Features --given Will2021Lin="query@2 around@4 center@2 area@1 keyval@2 name@0 New€York€City@s nwr@1 keyval@2 name@0 Pilgrim€Hill@s search@1 nwr@1 keyval@2 amenity@0 fountain@s maxdist@1 DIST_INTOWN@0 topx@1 1@0 qtype@1 findkey@1 name@s"\n\n'
            f"Available sources: {available_sources}\n"
            f"Available targets: {available_targets}\n"
        )
    )
    parser.add_argument(
        "--given",
        action="append",
        type=parse_given,
        help="Given sources for processing as name-value pairs with equal sign (=) as name-value separator",
    )
    parser.add_argument("--wanted", action="append", help="Given targets")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    ARGS = parse_args()
    main(**vars(ARGS))
