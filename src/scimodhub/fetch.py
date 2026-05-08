import logging
import json
from pathlib import Path
from typing import TextIO

import pandas as pd
import requests
from scimodhub.api import get_request

from scimodhub.models import MetadataRow
from scimodhub.utils import (
    EmptyDataError,
    get_tmp_dir,
    get_hub_dir,
    get_org_cfg_and_assembly,
    get_chrom_mapping,
    load_metadata,
)


logger = logging.getLogger(__name__)


def _overwrite_metadata(handle: TextIO, rows: list[MetadataRow]) -> None:
    dumps = [row.model_dump() for row in rows]
    pd.DataFrame(dumps).to_csv(handle, sep="\t", index=False, header=True)


def _write_modomics(handle: TextIO, version: str) -> None:
    response = requests.get(get_request(version, "modomics"))
    response.raise_for_status()
    d = dict()
    for val in response.json():
        d[val["modomics_sname"]] = val["id"]
    json.dump(d, handle, indent="\t")


def _write_metadata(
    handle: TextIO, version: str, taxa_id: int, assembly: str, include: list[str]
) -> None:
    response = requests.get(get_request(version, "dataset"))
    response.raise_for_status()
    df = pd.DataFrame(response.json()).astype({"taxa_id": int})
    df = df[df.taxa_id == taxa_id]
    if include:
        df = df[df.dataset_id.isin(include)]
    df["assembly"] = assembly
    df = df[
        [
            "dataset_id",
            "project_id",
            "taxa_id",
            "assembly",
            "rna",
            "modomics_sname",
            "tech",
            "cto",
        ]
    ]
    df.to_csv(handle, index=False, header=True, sep="\t")
    if df.empty:
        raise EmptyDataError("No EUFIDs/organism match this request.")


def _write_chroms(
    handle: TextIO, version: str, taxa_id: int, mapping: dict[str, str]
) -> None:
    response = requests.get(get_request(version, "chroms", parts=str(taxa_id)))
    response.raise_for_status()
    df = pd.DataFrame(response.json()).astype({"chrom": str, "size": int})
    df.chrom = df.chrom.map(mapping).fillna(df.chrom)
    df.to_csv(handle, index=False, header=False, sep="\t")


def _get_dataset(path: Path, version: str, dataset_id: str) -> None:
    with path.open("wb") as stream:
        with requests.get(
            get_request(version, "download", parts=dataset_id), stream=True
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                stream.write(chunk)


def _update_rows(
    rows: list[MetadataRow],
    data_dir: Path,
    version: str,
) -> list[MetadataRow]:
    upd_rows: list[MetadataRow] = []
    for row in rows:
        try:
            dataset_id = row.dataset_id
            bedrmod_path = Path(data_dir, f"{dataset_id}.bed")
            _get_dataset(bedrmod_path, version, dataset_id)
            upd_rows.append(
                MetadataRow(
                    dataset_id=dataset_id,
                    project_id=row.project_id,
                    taxa_id=row.taxa_id,
                    assembly=row.assembly,
                    rna=row.rna,
                    modomics_sname=row.modomics_sname,
                    tech=row.tech,
                    cto=row.cto,
                    bedrmod_path=bedrmod_path,
                )
            )
        except requests.exceptions.RequestException as err:
            logger.warning(f"Download: Skipping {dataset_id}: {err}")
    return upd_rows


def fetch_organism(
    config: dict,
    version: str,
    organism: str,
    include: list[str],
) -> None:
    """Fetch metadata and data for a given organism."""
    org_cfg, assembly = get_org_cfg_and_assembly(config, organism)

    # Directory setup
    tmp_dir = get_tmp_dir(config, organism)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    hub_dir = get_hub_dir(config, organism)
    hub_dir.mkdir(parents=True, exist_ok=True)

    # I/O
    if org_cfg["chroms"]["sizes"] is None:
        chrom_file = Path(org_cfg["chroms"]["mapping"])
        if not chrom_file.exists():
            logger.error(f"FileNotFoundError: No such file: '{chrom_file.as_posix()}'")
            return
        with chrom_file.open("r") as fh:
            chrom_mapping = get_chrom_mapping(fh)

        chrom_sizes = Path(tmp_dir, "chrom.sizes")
        logger.info(f"Writing: {chrom_sizes.as_posix()}")
        with chrom_sizes.open("w", encoding="utf-8") as fh:
            _write_chroms(fh, version, org_cfg["taxa_id"], chrom_mapping)
    else:
        logger.warning(f"Skipping: GET chroms for {organism}: 'chrom.sizes' is given.")

    if config["metadata_table"] is None:
        manifest = Path(tmp_dir, "manifest.tsv")
        logger.info(f"Writing: {manifest.as_posix()}")
        try:
            with manifest.open("w", encoding="utf-8") as fh:
                _write_metadata(fh, version, org_cfg["taxa_id"], assembly, include)
        except EmptyDataError as err:
            logger.warning(f"No metadata found for {organism}: {err}")
            return
    else:
        logger.warning(
            f"Skipping: GET dataset for {organism}: 'metadata_table' is given."
        )
        return

    # Download datasets
    data_dir = Path(tmp_dir, "datasets")
    data_dir.mkdir(exist_ok=True)

    with manifest.open("r") as fh:
        rows = load_metadata(fh, assembly, allow_missing=True)

    updated_rows = _update_rows(rows, data_dir, version)
    with manifest.open("w", encoding="utf-8") as fh:
        _overwrite_metadata(fh, updated_rows)


def fetch(config: dict, api_version: str, include: list[str]) -> None:
    """Build tracks."""
    for organism in config["genomes"]["include"]:
        fetch_organism(
            config,
            api_version,
            organism,
            include,
        )
    tmp_root = get_tmp_dir(config)
    modomics_file = Path(tmp_root, "modomics.json")
    logger.info(f"Writing: {modomics_file.as_posix()}")
    with modomics_file.open("w", encoding="utf-8") as fh:
        _write_modomics(fh, api_version)
