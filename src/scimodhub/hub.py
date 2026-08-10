from pathlib import Path
from typing import TextIO
from textwrap import dedent
from shutil import copyfile
from datetime import date

import pandas as pd

from scimodhub.models import (
    Subtrack,
    Hub,
    TrackDb,
    TrackHubConfig,
    TrackDbTrack,
    FacetedComposite,
)
from scimodhub.utils import get_type


def _get_mouse_over(hub_cfg: TrackHubConfig) -> str:
    score_str = "score"
    if hub_cfg.score_policy.lower() in ["zero", "coverage"]:
        score_str = "rawScore"
    mouse_over = "$name at $chrom:${chromStart} | "
    if hub_cfg.score_display:
        mouse_over += f"score: ${score_str} | "
    mouse_over += "coverage: $coverage | percent modified: $frequency"
    return mouse_over


def hub_config_from_dict(config: dict) -> TrackHubConfig:
    """Define hub configuration with defaults."""
    hub_cfg = config["hub"]
    desc_file = hub_cfg["hub"]["description"]
    if not Path(desc_file).exists():
        raise FileNotFoundError(f"No such file or directory: {desc_file}")
    img_file = hub_cfg["hub"]["image"]
    if img_file is not None and Path(img_file).exists():
        img = Path(img_file)
    else:
        img = None
    return Hub(
        name=hub_cfg["hub"]["name"],
        short_label=hub_cfg["hub"]["short_label"],
        long_label=hub_cfg["hub"]["long_label"],
        email=hub_cfg["hub"]["email"],
        description=Path(desc_file),
        image=img,
        public_address=hub_cfg["hub"]["public_address"],
    )


def track_db_config_from_dict(config: dict, label: str | None) -> TrackHubConfig:
    """Define hub configuration (trackDb) with defaults."""
    hub_cfg = config["hub"]
    display_cfg = config.get("display", {})
    short_label = hub_cfg["track_db"]["short_label"]
    long_label = hub_cfg["track_db"]["long_label"]
    track_db = TrackDb(
        name=hub_cfg["track_db"]["name"],
        short_label=f"{short_label} ({label})" if label else f"{short_label}",
        long_label=f"{long_label} ({label})" if label else f"{long_label}",
    )
    return TrackHubConfig(
        track_db=track_db,
        score_policy=str(hub_cfg.get("score_policy", "preserve")),
        score_display=str(hub_cfg.get("score_display", True)),
        max_check_boxes=int(hub_cfg.get("max_check_boxes", 20)),
        hide_empty=bool(hub_cfg.get("hide_empty_subtracks", True)),
        center_labels=bool(hub_cfg.get("center_labels_dense", True)),
        default_sort_field=hub_cfg.get("default_sort_field", "modification"),
        filters=hub_cfg.get("filters", None),
        toggle_on=hub_cfg.get("toggle_on", None),
        rgb_min=tuple(
            int(x) for x in display_cfg.get("frequency_color_min", "0,0,255").split(",")
        ),
        rgb_max=tuple(
            int(x) for x in display_cfg.get("frequency_color_max", "255,0,0").split(",")
        ),
    )


def write_metadata(handle: TextIO, subtracks: list[Subtrack]) -> None:
    """Write metadata.tsv."""
    rows = [
        {
            "dataset": f"{p.spec.primary_key}|{p.spec.dataset_title}",
            "_eufid": p.spec.dataset_id,
            "modification": p.spec.modification,
            "biosample": p.spec.cto,
            "technology": p.spec.tech,
        }
        for p in subtracks
    ]
    pd.DataFrame(rows).to_csv(handle, sep="\t", index=False, header=True)


def write_trackdb(
    handle: TextIO,
    subtracks: list[Subtrack],
    hub_cfg: TrackHubConfig,
) -> None:
    """Write track hub (trackDb)."""
    tracks = []
    for track in sorted(
        subtracks,
        key=lambda t: (
            t.spec.modification,
            t.spec.cto,
            t.spec.tech,
            t.spec.dataset_id,
        ),
    ):
        spec = track.spec
        hub_dir = spec.hub_dir
        bb_path = Path(hub_dir, f"{spec.primary_key}.bb")
        tracks.append(
            TrackDbTrack(
                name=spec.subtrack,
                parent=hub_cfg.track_db.name,
                toggle_on=spec.toggle_on,
                short_label=spec.short_label,
                long_label=spec.long_label,
                big_data_url=bb_path.relative_to(hub_dir).as_posix(),
                url=f"https://scimodom.dieterichlab.org/browse/{spec.dataset_id}",
                url_label=f"Sci-ModoM dataset record ({spec.dataset_id})",
            )
        )

    composite = FacetedComposite(
        name=hub_cfg.track_db.name,
        short_label=hub_cfg.track_db.short_label,
        long_label=hub_cfg.track_db.long_label,
        track_type=f"bigBed {get_type(hub_cfg)}",
        meta_data_url="metadata.tsv",
        primary_key="dataset",
        max_check_boxes=hub_cfg.max_check_boxes,
        default_sort_field=hub_cfg.default_sort_field,
        center_labels=hub_cfg.center_labels,
        hide_empty=hub_cfg.hide_empty,
        date=date.today(),
        mouse_over=_get_mouse_over(hub_cfg),
        filters=hub_cfg.filters,
        tracks=tuple(tracks),
    )
    handle.write(composite.render())


def write_hub_files(
    hub_files: dict[str, TextIO], hub_cfg: Hub, genomes: tuple[str, str]
) -> None:
    """Write hub files."""
    hub_files["hub.txt"].write(dedent(f"""\
    hub {hub_cfg.name}
    shortLabel {hub_cfg.short_label}
    longLabel {hub_cfg.long_label}
    genomesFile genomes.txt
    email {hub_cfg.email}
    descriptionUrl description.html
    """))
    description = hub_cfg.description.read_text()
    if hub_cfg.public_address is not None and hub_cfg.image is not None:
        img = hub_cfg.image.name
        description = description.replace(
            f'<img src="{img}"', f'<img src="{hub_cfg.public_address}/{img}"'
        )
    hub_files["description.html"].write(description)
    for assembly, rel_path in genomes:
        hub_files["genomes.txt"].write(dedent(f"""\
                genome {assembly}
                trackDb {rel_path}/trackDb.txt

                """))


def copy_files(hub_root: Path, hub_cfg: Hub, genomes: tuple[str, str]) -> None:
    """Copy files and images."""
    for _, rel_str in genomes:
        # TODO: we need the composite's track name...
        rel_path = Path(hub_root, rel_str)
        track_db = Path(rel_path, "trackDb.txt")
        name = track_db.read_text().splitlines()[0].partition("track")[2].strip()
        copyfile(
            Path(hub_root, "description.html"),
            Path(rel_path, f"{name}.html"),
        )
    if hub_cfg.image is not None:
        img = hub_cfg.image
        copyfile(img, Path(hub_root, img.name))
