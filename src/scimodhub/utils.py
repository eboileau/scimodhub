import re
from pathlib import Path
from typing import TextIO

import pandas as pd

from scimodhub.models import MetadataRow, TrackHubConfig


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


def load_metadata(handle: TextIO, assembly: str) -> list[MetadataRow]:
    """Read metadata table."""
    df = pd.read_csv(handle, sep="\t")
    rows: list[MetadataRow] = []
    for _, r in df.iterrows():
        rows.append(
            MetadataRow(
                dataset_id=str(r["dataset_id"]),
                project_id=str(r["project_id"]),
                taxa_id=int(r["taxa_id"]),
                assembly=assembly,
                rna=str(r["rna"]),
                modomics_sname=str(r["modomics_sname"]),
                tech=str(r["tech"]),
                cto=str(r["cto"]),
                bedrmod_path=Path(str(r["bedrmod_path"])),
            )
        )
    return rows


def get_org_cfg_and_assembly(config: dict, organism: str) -> tuple[dict, str]:
    """Get organism configuration and assembly."""
    org_cfg = config["genomes"][organism]
    assembly = list(org_cfg["assembly"].keys())[0]
    return org_cfg, assembly


def get_tmp_dir(config: dict, organism: str) -> Path:
    """Create path to temporary directory."""
    org_cfg, assembly = get_org_cfg_and_assembly(config, organism)
    parent = re.sub(r"[^a-zA-Z0-9]", "", organism)
    return Path(config["working_dir"], parent, org_cfg["assembly"][assembly])


def get_hub_dir(config: dict, organism: str, root: bool = False) -> Path:
    """Create path to hub directory."""
    org_cfg, assembly = get_org_cfg_and_assembly(config, organism)
    hub_name = re.sub(r"[^a-zA-Z0-9]", "", config["hub"]["hub"]["name"])
    hub_parent = re.sub(r"[^a-zA-Z0-9]", "", organism)
    hub_child = re.sub(r"[^a-zA-Z0-9]", "", org_cfg["assembly"][assembly])
    hub_dir = Path(config["staging_dir"], hub_name, hub_parent, hub_child)
    if root:
        return hub_dir.parents[1]
    else:
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
    if policy == "zero":
        return "9+3"
    return "9+2"


# def get_seqids(path: str, assembly: str) -> list[str]:
#     """Return chromosomes for a given assembly as a list."""
#     with open(Path(path, assembly, "chrom.sizes") as fp:
#         lines = fp.readlines()
#     return [line.split()[0] for line in lines]
