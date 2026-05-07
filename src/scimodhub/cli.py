import argparse
import sys
import yaml
import shutil
from pathlib import Path

import logging

from scimodhub.build import build_tracks
from scimodhub.fetch import fetch
from scimodhub.utils import add_logging_options, update_logging

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="""Provide a wrapper to create track hubs.""",
    )
    parser.add_argument(
        "--config", required=True, help="Required YAML configuration file."
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    # fetch
    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Fetch data from Sci-ModoM.",
    )
    fetch_parser.add_argument(
        "-v",
        "--api-version",
        type=str,
        default="v0",
        help="Sci-ModoM API version",
    )
    fetch_parser.add_argument(
        "-e",
        "--eufid",
        type=str,
        nargs="*",
        help="Fetch only these datasets.",
    )
    # build
    build_parser = subparsers.add_parser("build", help="Build a track hub")
    build_parser.add_argument(
        "--skip-call",
        action="store_true",
        help="Create hub but skip calls to bedToBigBed.",
    )
    build_parser.add_argument(
        "-w",
        "--max-workers",
        type=int,
        default=None,
        help="Max. worker threads to execute calls asynchronously.",
    )
    add_logging_options(parser)
    args = parser.parse_args()
    update_logging(args)

    logger.info("[scimodhub]: {}".format(" ".join(sys.argv)))

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    if args.cmd == "fetch":
        fetch(config, args.api_version, args.eufid)
    else:
        if not args.skip_call:
            if shutil.which("bedToBigBed") is None:
                logger.error("FileNotFoundError: No such file: 'bedToBigBed'")
                return
        build_tracks(config, args.skip_call, args.max_workers)


if __name__ == "__main__":
    main()
