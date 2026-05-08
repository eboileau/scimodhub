import logging
from pathlib import Path
from typing import Generator, TextIO
import shlex
from subprocess import run, CalledProcessError

from scimodhub.utils import frequency_to_rgb_triplet, get_type
from scimodhub.models import (
    EufRecord,
    Subtrack,
    TrackHubConfig,
    AutoSqlField,
    AutoSqlSchema,
)


logger = logging.getLogger(__name__)


def _get_as_schema(hub_cfg: TrackHubConfig) -> AutoSqlSchema:
    fields = (
        AutoSqlField(astype="string", name="chrom", description="Chromosome"),
        AutoSqlField(
            astype="uint",
            name="chromStart",
            description="Modification start position",
        ),
        AutoSqlField(
            astype="uint", name="chromEnd", description="Modification end position"
        ),
        AutoSqlField(
            astype="string", name="name", description="Modification short name"
        ),
        AutoSqlField(
            astype="uint",
            name="score",
            description="bedRMod score or 0; off",
        ),
        AutoSqlField(astype="char[1]", name="strand", description="Strand"),
        AutoSqlField(astype="uint", name="thickStart", description="Thick start"),
        AutoSqlField(astype="uint", name="thickEnd", description="Thick end"),
        AutoSqlField(
            astype="uint",
            name="itemRgb",
            description="Blue (0) to red (100) percent modified",
        ),
        AutoSqlField(astype="uint", name="coverage", description="Coverage"),
        AutoSqlField(astype="float", name="frequency", description="Percent modified"),
        AutoSqlField(astype="uint", name="rawScore", description="bedRmod score"),
    )
    policy = hub_cfg.score_policy.lower()
    if policy not in ["zero", "coverage"]:
        fields = fields[:-1]
    return AutoSqlSchema(
        table="bedRMod",
        title="bigRMod bedRMod",
        fields=fields,
    )


def _write_autosql(
    handle: TextIO,
    hub_cfg: TrackHubConfig,
) -> None:
    schema = _get_as_schema(hub_cfg)
    handle.write(schema.render())


def _get_score(record: EufRecord, policy: str) -> tuple[int, int | None]:
    policy = policy.lower()
    if policy == "zero":
        return 0, record.score
    elif policy == "coverage":
        return 0, record.coverage
    else:
        return record.score, None


def _generate_records(
    hub_cfg: TrackHubConfig,
    chrom_mapping: dict[str, str],
    records: Generator[EufRecord, None, None],
) -> Generator[str, None, None]:
    for record in records:
        score, raw_score = _get_score(record, hub_cfg.score_policy)
        parts = [
            chrom_mapping[record.chrom],
            str(record.start),
            str(record.end),
            record.name,
            str(score),
            record.strand,
            str(record.thick_start),
            str(record.thick_end),
            frequency_to_rgb_triplet(
                record.frequency, hub_cfg.rgb_min, hub_cfg.rgb_max
            ),
            str(record.coverage),
            # f"{record.frequency:.2f}",
            str(record.frequency),
        ]
        if raw_score is not None:
            parts.append(str(raw_score))
        yield "\t".join(parts) + "\n"


def _write_bed(
    handle: TextIO,
    hub_cfg: TrackHubConfig,
    chrom_mapping: dict[str, str],
    records: Generator[EufRecord, None, None],
) -> None:
    for record in _generate_records(hub_cfg, chrom_mapping, records):
        handle.write(record)


def _run(
    cmd: str,
    caller: str,
    check: bool = True,
    capture_output: bool = True,
    text: bool = True,
    stdout: TextIO | None = None,
) -> None:
    try:
        run(
            shlex.split(cmd),
            check=check,
            capture_output=capture_output,
            text=text,
            stdout=stdout,
        )
    except FileNotFoundError as exc:
        raise Exception(f"Process failed: {caller} could not be found!") from exc
    except CalledProcessError as exc:
        raise Exception(f"Process failed with {exc.stderr}")


def _sort_bed(handle: TextIO, bed_path: str) -> None:
    cmd = f"sort -k1,1 -k2,2n {bed_path}"
    _run(cmd, "sort", capture_output=False, stdout=handle)


def _convert_to_bigbed(
    sorted_bed_path: str,
    chrom_sizes: str,
    autosql_path: str,
    bb_path: str,
    bed_type: str,
) -> None:
    cmd = (
        f"bedToBigBed -tab -as={autosql_path} -type=bed{bed_type} "
        f"{sorted_bed_path} {chrom_sizes} {bb_path}"
    )
    _run(cmd, "bedToBigBed")


def build_subtrack(
    subtrack: Subtrack,
    hub_cfg: TrackHubConfig,
    chrom_mapping: dict[str, str],
    chrom_sizes: Path | None,
    skip_call: bool,
) -> int:
    """Write files and convert to bigBed."""
    spec = subtrack.spec
    records = subtrack.records
    bed_path = Path(spec.tmp_dir, f"{spec.primary_key}.bed")
    as_path = Path(spec.tmp_dir, f"{spec.primary_key}.as")
    sorted_bed_path = Path(spec.tmp_dir, f"{spec.primary_key}.sorted.bed")
    bb_path = Path(spec.hub_dir, f"{spec.primary_key}.bb")
    with bed_path.open("w", encoding="utf-8") as fh:
        _write_bed(fh, hub_cfg, chrom_mapping, records)
    with as_path.open("w", encoding="utf-8") as fh:
        _write_autosql(fh, hub_cfg)
    if skip_call:
        logger.warning("Skipping call to bedToBigBed!")
    else:
        with sorted_bed_path.open("w", encoding="utf-8") as fh:
            _sort_bed(fh, bed_path.as_posix())
        if chrom_sizes is not None:
            bed_type = get_type(hub_cfg).replace(" ", "")
            _convert_to_bigbed(
                sorted_bed_path.as_posix(),
                chrom_sizes.as_posix(),
                as_path.as_posix(),
                bb_path.as_posix(),
                bed_type,
            )
    return 1
