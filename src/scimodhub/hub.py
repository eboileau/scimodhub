from pathlib import Path
from typing import TextIO
from textwrap import dedent
from shutil import copyfile

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
    mouse_over = "$name | "
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
    )


def track_db_config_from_dict(config: dict, label: str) -> TrackHubConfig:
    """Define hub configuration (trackDb) with defaults."""
    hub_cfg = config["hub"]
    display_cfg = config.get("display", {})
    short_label = hub_cfg["track_db"]["short_label"]
    long_label = hub_cfg["track_db"]["long_label"]
    track_db = TrackDb(
        name=hub_cfg["track_db"]["name"],
        short_label=f"{short_label} ({label})",
        long_label=f"{long_label} ({label})",
    )
    return TrackHubConfig(
        track_db=track_db,
        score_policy=str(hub_cfg.get("score_policy", "preserve")),
        score_display=str(hub_cfg.get("score_policy", True)),
        max_check_boxes=int(hub_cfg.get("max_check_boxes", 20)),
        hide_empty=bool(hub_cfg.get("hide_empty_subtracks", True)),
        center_labels=bool(hub_cfg.get("center_labels_dense", True)),
        all_button_pair=bool(hub_cfg.get("all_button_pair", True)),
        drag_and_drop=bool(hub_cfg.get("drag_and_drop_subtracks", True)),
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
            "track": p.spec.primary_key,
            "_eufid": p.spec.dataset_id,
            "modification": p.spec.modification,
            "cell": p.spec.cto,
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
                short_label=spec.short_label,
                long_label=spec.long_label,
                big_data_url=bb_path.relative_to(hub_dir).as_posix(),
                parent=hub_cfg.track_db.name,
                track_type=f"bigBed {get_type(hub_cfg)}",
                mouse_over=_get_mouse_over(hub_cfg),
            )
        )

    composite = FacetedComposite(
        name=hub_cfg.track_db.name,
        short_label=hub_cfg.track_db.short_label,
        long_label=hub_cfg.track_db.long_label,
        track_type=f"bigBed {get_type(hub_cfg)}",
        meta_data_url="metadata.tsv",
        primary_key="track",
        max_check_boxes=hub_cfg.max_check_boxes,
        tracks=tuple(tracks),
        all_button_pair=hub_cfg.all_button_pair,
        center_labels=hub_cfg.center_labels,
        drag_and_drop=hub_cfg.drag_and_drop,
        hide_empty=hub_cfg.hide_empty,
    )
    handle.write(composite.render())


def write_hub_files(
    hub_files: dict[str, TextIO], hub_cfg: Hub, genomes: tuple[str, str]
) -> None:
    """Write hub files."""
    hub_files["hub.txt"].write(
        dedent(
            f"""\
    hub {hub_cfg.name}
    shortLabel {hub_cfg.short_label}
    longLabel {hub_cfg.long_label}
    genomesFile genomes.txt
    email {hub_cfg.email}
    descriptionUrl description.html
    """
        )
    )
    hub_files["description.html"].write(hub_cfg.description.read_text())
    for assembly, rel_path in genomes:
        hub_files["genomes.txt"].write(
            dedent(
                f"""\
                genome {assembly}
                trackDb {rel_path}/trackDb.txt

                """
            )
        )


def copy_img(hub_root: Path, hub_cfg: Hub) -> None:
    """Copy image for description."""
    if hub_cfg.image is not None:
        img = hub_cfg.image
        copyfile(img, Path(hub_root, img.name))
