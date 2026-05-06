import argparse
import sys
import yaml
import shutil
from pathlib import Path

import logging

from scimodhub.build import build_tracks


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
    fetch_parser = subparsers.add_parser("fetch", help="Fetch data from Sci-ModoM.")
    fetch_parser.add_argument(
        "--api-version", type=str, default="v0", help="Sci-ModoM API version"
    )
    fetch_parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Download metadata only; otherwise also download bedRMod files.",
    )
    # get for organisms in config
    # get chrom size if not specified, write to work dir same as for build (utils) CONVERT !!!:
    # api version, use dict to map end points with version, now only v0 (module) - option
    # write browse to work dir, and final manifest from config (dont overwrite)
    # get each bedrmod file from manifest, log any missing, update manifest - option (only metadata and/or data)
    build_parser = subparsers.add_parser("build", help="Build a track hub")
    build_parser.add_argument(
        "--skip-call",
        action="store_true",
        help="Create hub but skip calls to bedToBigBed.",
    )
    build_parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Max. worker threads to execute calls asynchronously.",
    )
    args = parser.parse_args()

    logger.info("[scimodhub]: {}".format(" ".join(sys.argv)))

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    if args.cmd == "fetch":
        pass
    else:
        if not args.skip_call:
            if shutil.which("bedToBigBed") is None:
                logger.error("FileNotFoundError: No such file: 'bedToBigBed'")
                return
        build_tracks(config, args.skip_call, args.max_workers)


if __name__ == "__main__":
    main()
