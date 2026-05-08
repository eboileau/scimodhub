import re
import sys
import logging
from pathlib import Path
from typing import TextIO

import pandas as pd

from scimodhub.models import MetadataRow, TrackHubConfig

logger = logging.getLogger(__name__)


class EmptyDataError(Exception):
    """Handle empty dataframe."""

    pass


def _rgb_triplet(r: int, g: int, b: int) -> str:
    return f"{int(r)},{int(g)},{int(b)}"


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def frequency_to_rgb_triplet(
    frequency: float,
    min_rgb: tuple[int, int, int] = (0, 0, 255),
    max_rgb: tuple[int, int, int] = (255, 0, 0),
) -> str:
    """Convert frequency to RGB triplet."""
    pct = int(round(_clamp(frequency, 0.0, 100.0)))
    t = pct / 100.0
    r = round(min_rgb[0] + (max_rgb[0] - min_rgb[0]) * t)
    g = round(min_rgb[1] + (max_rgb[1] - min_rgb[1]) * t)
    b = round(min_rgb[2] + (max_rgb[2] - min_rgb[2]) * t)
    return _rgb_triplet(r, g, b)


def load_metadata(
    handle: TextIO, assembly: str, allow_missing: bool = False
) -> list[MetadataRow]:
    """Read metadata table."""
    df = pd.read_csv(handle, sep="\t")
    has_assembly = "assembly" in df
    has_bedrmod = "bedrmod_path" in df

    def _get_assembly(r: pd.Series) -> str:
        if has_assembly:
            given_assembly = str(r["assembly"])
            if given_assembly != assembly:
                raise ValueError(
                    f"Assembly: {given_assembly} (metadata) != {assembly} (config)."
                )
            return given_assembly
        return assembly

    def _get_bedrmod_path(r: pd.Series) -> Path | None:
        if has_bedrmod:
            return Path(str(r["bedrmod_path"]))
        else:
            if allow_missing:
                return None
            else:
                raise ValueError("Missing 'bedrmod_path'")

    rows: list[MetadataRow] = []
    for _, r in df.iterrows():
        try:
            rows.append(
                MetadataRow(
                    dataset_id=str(r["dataset_id"]),
                    project_id=str(r["project_id"]),
                    taxa_id=int(r["taxa_id"]),
                    assembly=_get_assembly(r),
                    rna=str(r["rna"]),
                    modomics_sname=str(r["modomics_sname"]),
                    tech=str(r["tech"]),
                    cto=str(r["cto"]),
                    bedrmod_path=_get_bedrmod_path(r),
                )
            )
        except ValueError as err:
            logger.warning(f"Skipping {r['dataset_id']}: {err}")
    return rows


def get_org_cfg_and_assembly(config: dict, organism: str) -> tuple[dict, str]:
    """Get organism configuration and assembly."""
    org_cfg = config["genomes"][organism]
    assembly = list(org_cfg["assembly"].keys())[0]
    return org_cfg, assembly


def get_tmp_dir(config: dict, organism: str | None = None) -> Path:
    """Create path to temporary directory."""
    tmp_root = Path(config["working_dir"])
    if organism is None:
        return tmp_root
    org_cfg, assembly = get_org_cfg_and_assembly(config, organism)
    parent = re.sub(r"[^a-zA-Z0-9]", "", organism)
    return Path(tmp_root, parent, org_cfg["assembly"][assembly])


def get_hub_dir(config: dict, organism: str | None = None) -> Path:
    """Create path to hub directory."""
    hub_name = re.sub(r"[^a-zA-Z0-9]", "", config["hub"]["hub"]["name"])
    hub_root = Path(config["staging_dir"], hub_name)
    if organism is None:
        return hub_root
    org_cfg, assembly = get_org_cfg_and_assembly(config, organism)
    hub_parent = re.sub(r"[^a-zA-Z0-9]", "", organism)
    hub_child = re.sub(r"[^a-zA-Z0-9]", "", org_cfg["assembly"][assembly])
    hub_dir = Path(hub_root, hub_parent, hub_child)
    return hub_dir


def get_chrom_mapping(handle: TextIO) -> dict[str, str]:
    """Convert chrom mapping to dictionary.

    The mapping is Ensembl->UCSC.
    The file must be tab-separated, w/o header.
    """
    df = pd.read_csv(
        handle, sep="\t", header=None, names=["ensembl", "ucsc"], dtype=str
    )
    return dict(zip(df["ensembl"], df["ucsc"]))


def get_type(hub_cfg: TrackHubConfig) -> str:
    """Get bed/bigBed type according to score policy.

    NOTE: default is 9+2 (bedRMod), if score policy
    is "zero", score is added as 12th field.
    """
    policy = hub_cfg.score_policy.lower()
    if policy in ["zero", "coverage"]:
        return "9 + 3"
    return "9 + 2"


def add_logging_options(parser, default_log_file=""):
    """Add logging options."""
    logging_options = parser.add_argument_group("logging options")
    logging_level_choices = [
        "NOTSET",
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ]
    logging_options.add_argument(
        "--log-file", help="Log to file.", default=default_log_file
    )
    logging_options.add_argument(
        "--log-stdout", help="Log to stdout.", action="store_true"
    )
    logging_options.add_argument(
        "--logging-level",
        help="Level for all logs.",
        choices=logging_level_choices,
        default="WARNING",
    )


def update_logging(
    args, logger=None, format_str="%(levelname)-8s %(name)-8s %(asctime)s : %(message)s"
):
    """Update the logging options in args."""
    if logger is None:
        logger = logging.getLogger("")

    logger.handlers = []
    level = logging.getLevelName(args.logging_level)
    logger.setLevel(level)

    if len(args.log_file) > 0:
        h = logging.FileHandler(args.log_file)
        formatter = logging.Formatter(format_str)
        h.setFormatter(formatter)
        if args.logging_level != "NOTSET":
            level = logging.getLevelName(args.logging_level)
            h.setLevel(level)
        logger.addHandler(h)

    if args.log_stdout:
        h = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(format_str)
        h.setFormatter(formatter)
        if args.logging_level != "NOTSET":
            level = logging.getLevelName(args.logging_level)
            h.setLevel(level)
        logger.addHandler(h)

    h = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(format_str)
    h.setFormatter(formatter)
    if args.logging_level != "NOTSET":
        level = logging.getLevelName(args.logging_level)
        h.setLevel(level)
    logger.addHandler(h)
