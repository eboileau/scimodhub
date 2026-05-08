import os
import re
import json
import logging
from pathlib import Path
from typing import Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack

from scimodhub.models import (
    MetadataRow,
    TrackHubConfig,
    SubtrackSpec,
    Subtrack,
    EufRecord,
)
from scimodhub.utils import (
    EmptyDataError,
    load_metadata,
    get_tmp_dir,
    get_hub_dir,
    get_org_cfg_and_assembly,
    get_chrom_mapping,
)
from scimodhub.hub import (
    hub_config_from_dict,
    track_db_config_from_dict,
    write_metadata,
    write_trackdb,
    write_hub_files,
)
from scimodhub.bedrmod import EufImporter
from scimodhub.bigbed import build_subtrack

logger = logging.getLogger(__name__)


class SpecsError(Exception):
    """To handle inconsistencies in bedRMod header."""

    pass


def _get_records(
    records: list[EufRecord], modification: str
) -> Generator[EufRecord, None, None]:
    for record in records:
        if record.name == modification:
            yield record


def _validate_header(
    importer: EufImporter, dataset_id: str, assembly: str, euf_versions: list[str]
) -> None:
    FILE_FORMAT_VERSION_REGEXP = re.compile(r".*?([0-9.]+)\Z")
    # validate format and assembly
    file_format = importer.get_header("fileformat")
    if file_format is None:
        raise SpecsError("Failed to parse version from header (1).")
    match = FILE_FORMAT_VERSION_REGEXP.match(file_format)
    if match is None:
        raise SpecsError("Failed to parse version from header (2).")
    version = match.group(1)
    if version not in euf_versions:
        raise SpecsError(f"Unknown or outdated version {version}.")
    header_assembly = importer.get_header("assembly")
    if header_assembly != assembly:
        raise SpecsError(f"Assembly: {header_assembly} ({dataset_id}) != {assembly}.")


def _add_subtrack_spec(
    row: MetadataRow,
    hub_cfg: TrackHubConfig,
    modification: str,
    modomics: dict[str, str],
    hub_root: Path,
    hub_dir: Path,
    tmp_dir: Path,
) -> SubtrackSpec:
    sub = modomics[modification] if modomics else modification
    tid = f"{row.dataset_id}{sub}"
    return SubtrackSpec(
        primary_key=tid,
        subtrack=f"{hub_cfg.track_db.name}_{tid}",
        dataset_id=row.dataset_id,
        rna=row.rna,
        modification=modification,
        tech=row.tech,
        cto=row.cto,
        short_label=f"{modification}",
        long_label=f"EUFID:{row.dataset_id} | {modification} {row.cto} {row.tech}",
        hub_root=hub_root,
        hub_dir=hub_dir,
        tmp_dir=tmp_dir,
    )


def _prepare_subtracks(
    rows: list[MetadataRow],
    hub_cfg: TrackHubConfig,
    versions: list[str],
    modomics: dict[str, str],
    hub_root: Path,
    hub_dir: Path,
    tmp_dir: Path,
) -> list[Subtrack]:
    subtracks: list[Subtrack] = []
    for row in rows:
        try:
            with open(row.bedrmod_path) as fp:
                importer = EufImporter(stream=fp, source=row.bedrmod_path)
                _validate_header(importer, row.dataset_id, row.assembly, versions)
                records = [record for record in importer.parse()]
                # parse records - "split" by modification for faceting
                for modification in row.modomics_sname.split(","):
                    spec = _add_subtrack_spec(
                        row, hub_cfg, modification, modomics, hub_root, hub_dir, tmp_dir
                    )
                    subtracks.append(
                        Subtrack(spec=spec, records=_get_records(records, modification))
                    )
        except SpecsError as err:
            logger.warning(f"Skipping {row.dataset_id}: {err}")
    return subtracks


def build_organism_tracks(
    config: dict,
    organism: str,
    modomics: dict[str, str],
    skip_call: bool = False,
    max_workers: int | None = None,
) -> tuple[str, str]:
    """Build tracks for a given organism."""
    org_cfg, assembly = get_org_cfg_and_assembly(config, organism)
    euf_versions = config["euf_compatible_versions"]

    # Directory setup
    tmp_dir = get_tmp_dir(config, organism)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    hub_dir = get_hub_dir(config, organism)
    hub_dir.mkdir(parents=True, exist_ok=True)
    hub_root = get_hub_dir(config)

    # I/O
    chrom_file = Path(org_cfg["chrom"]["mapping"])
    if not chrom_file.exists():
        raise FileNotFoundError(
            f"FileNotFoundError: No such file: '{chrom_file.as_posix()}'."
        )
    with chrom_file.open("r") as fh:
        chrom_mapping = get_chrom_mapping(fh)

    chrom_sizes = None
    if not skip_call:
        if org_cfg["chrom"]["sizes"] is None:
            chrom_sizes = Path(tmp_dir, "chrom.sizes")
        else:
            chrom_sizes = Path(org_cfg["chrom"]["sizes"])
        if not chrom_sizes.exists():
            raise FileNotFoundError(
                f"FileNotFoundError: No such file: '{chrom_sizes.as_posix()}'."
            )

    if config["metadata_table"] is None:
        manifest = Path(tmp_dir, "manifest.tsv")
    else:
        manifest = Path(config["metadata_table"])
    if not manifest.exists():
        raise FileNotFoundError(
            f"FileNotFoundError: No such file: '{manifest.as_posix()}'."
        )
    with manifest.open("r") as fh:
        rows = load_metadata(fh, assembly)
    rows = [r for r in rows if r.taxa_id == org_cfg["taxa_id"]]
    if not rows:
        raise EmptyDataError(f"No metadata found for {org_cfg['taxa_id']}.")

    hub_cfg = track_db_config_from_dict(config, org_cfg["label"])
    subtracks = _prepare_subtracks(
        rows, hub_cfg, euf_versions, modomics, hub_root, hub_dir, tmp_dir
    )
    with open(Path(hub_dir, "metadata.tsv"), "w") as fh:
        write_metadata(fh, subtracks)

    def _task(subtrack: Subtrack):
        return build_subtrack(
            subtrack=subtrack,
            hub_cfg=hub_cfg,
            chrom_mapping=chrom_mapping,
            chrom_sizes=chrom_sizes,
            skip_call=skip_call,
        )

    workers = max_workers or os.cpu_count()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_task, p) for p in subtracks]
        for future in as_completed(futures):
            future.result()

    with open(Path(hub_dir, "trackDb.txt"), "w") as fh:
        write_trackdb(fh, subtracks, hub_cfg)

    return org_cfg["assembly"][assembly], hub_dir.relative_to(hub_root).as_posix()


def build_tracks(
    config: dict,
    skip_call: bool = False,
    max_workers: int | None = None,
) -> None:
    """Build tracks."""
    hub_root = get_hub_dir(config)
    hub_cfg = hub_config_from_dict(config)
    tmp_root = get_tmp_dir(config)
    modomics_file = Path(tmp_root, "modomics.json")
    if modomics_file.exists():
        try:
            with modomics_file.open("r") as fh:
                modomics = json.load(fh)
            logger.info(f"Using: {modomics_file.as_posix()} (MODOMICS code).")
        except Exception:
            modomics = dict()
    genomes = []
    for organism in config["genomes"]["include"]:
        try:
            assembly, rel_path = build_organism_tracks(
                config,
                organism,
                modomics,
                skip_call=skip_call,
                max_workers=max_workers,
            )
            genomes.append((assembly, rel_path))
        except (FileNotFoundError, EmptyDataError) as err:
            logger.warning(f"Skipping {organism}: {err}")

    if genomes:
        Path(hub_root, "genomes.txt").unlink(missing_ok=True)
        with ExitStack() as stack:
            files = {
                f: stack.enter_context(open(Path(hub_root, f), m, encoding="utf-8"))
                for f, m in zip(
                    ["hub.txt", "description.html", "genomes.txt"],
                    ["w", "w", "a"],
                )
            }
            write_hub_files(files, hub_cfg, genomes)
