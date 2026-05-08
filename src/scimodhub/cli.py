import argparse
import sys
import yaml
import shutil
from pathlib import Path

import logging

from scimodhub.build import build_tracks
from scimodhub.fetch import fetch
from scimodhub.utils import (
    add_logging_options,
    update_logging,
    get_tmp_dir,
    get_hub_dir,
)

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
    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove temporary directories.",
    )
    clean_parser.add_argument(
        "--all",
        action="store_true",
        help="Delete both 'working' (temporary) and 'staging' directories.",
    )
    add_logging_options(parser)
    args = parser.parse_args()
    update_logging(args)

    logger.info("[scimodhub]: {}".format(" ".join(sys.argv)))

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    if args.cmd == "fetch":
        fetch(config, args.api_version, args.eufid)
    elif args.cmd == "build":
        if not args.skip_call:
            if shutil.which("bedToBigBed") is None:
                logger.error("FileNotFoundError: No such file: 'bedToBigBed'")
                return
        build_tracks(config, args.skip_call, args.max_workers)
    elif args.cmd == "clean":
        tmp_root = get_tmp_dir(config)
        shutil.rmtree(tmp_root, ignore_errors=True)
        if args.all:
            hub_root = get_hub_dir(config)
            proceed = input(f"Delete {hub_root.as_posix()}?")
            if proceed.lower() in ["y", "yes"]:
                try:
                    shutil.rmtree(hub_root)
                except Exception as err:
                    logging.error(f"Cannot remove directory: {err}")


if __name__ == "__main__":
    main()
