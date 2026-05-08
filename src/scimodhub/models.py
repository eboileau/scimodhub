from typing import Annotated, Self, Iterable
from pydantic import BaseModel, Field, EmailStr, model_validator
from pathlib import Path


# metadata

ProjectId = Annotated[str, Field(min_length=8, max_length=8)]
DatasetId = Annotated[str, Field(min_length=12, max_length=12)]


class MetadataRow(BaseModel):
    """Metadata."""

    dataset_id: DatasetId
    project_id: ProjectId
    taxa_id: Annotated[int, Field(gt=0)]
    assembly: Annotated[str, Field(min_length=1, max_length=128)]
    rna: Annotated[str, Field(min_length=1, max_length=32)]
    modomics_sname: Annotated[str, Field(min_length=1, max_length=255)]
    tech: Annotated[str, Field(min_length=1, max_length=255)]
    cto: Annotated[str, Field(min_length=1, max_length=255)]
    bedrmod_path: Path | None


# bedRMod

NonNegativInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
PercentFloat = Annotated[float, Field(ge=0, le=100)]


class EufRecord(BaseModel):
    """EUF/bedRMod record."""

    chrom: Annotated[str, Field(min_length=1, max_length=128)]
    start: NonNegativInt
    end: NonNegativInt
    name: Annotated[str, Field(min_length=1, max_length=128)]
    score: NonNegativInt
    # score: PositiveInt
    strand: Annotated[str, Field(pattern=r"^[\+\-\.]$")]
    thick_start: NonNegativInt
    thick_end: NonNegativInt
    item_rgb: str
    coverage: PositiveInt
    frequency: PercentFloat

    @model_validator(mode="after")
    def check_start_end(self) -> Self:
        if self.end <= self.start:
            raise ValueError(
                f"The value of 'end' ({self.end}) must be greater than the value of 'start' ({self.start})"
            )
        return self

    @model_validator(mode="after")
    def check_thick_start_end(self) -> Self:
        if self.thick_end <= self.thick_start:
            raise ValueError(
                f"The value of 'thickEnd' ({self.thick_end}) must be greater than the value of 'thickStart' ({self.thick_start})"
            )
        return self


# tracks and track hub


class Hub(BaseModel):
    """Hub."""

    name: Annotated[str, Field(pattern=r"[a-zA-Z0-9]")]
    short_label: Annotated[
        str, Field(min_length=1, max_length=17, pattern=r"[a-zA-Z0-9 ]")
    ]
    long_label: Annotated[
        str, Field(min_length=1, max_length=80, pattern=r"[a-zA-Z0-9 ]")
    ]
    email: EmailStr


class TrackDb(BaseModel):
    """TrackDb."""

    name: Annotated[str, Field(pattern=r"[a-zA-Z0-9]")]
    short_label: Annotated[
        str, Field(min_length=1, max_length=17, pattern=r"[a-zA-Z0-9 ]")
    ]
    long_label: Annotated[
        str, Field(min_length=1, max_length=76, pattern=r"[a-zA-Z0-9 ]")
    ]


class TrackHubConfig(BaseModel):
    """Track Hub."""

    track_db: TrackDb
    score_policy: str
    max_check_boxes: int
    hide_empty: bool
    center_labels: bool
    all_button_pair: bool
    drag_and_drop: bool
    rgb_min: tuple[int, int, int]
    rgb_max: tuple[int, int, int]


class SubtrackSpec(BaseModel):
    """Subtrack metadata."""

    primary_key: Annotated[str, Field(pattern=r"[a-zA-Z0-9_-]")]
    subtrack: Annotated[str, Field(pattern=r"[a-zA-Z0-9_-]")]
    dataset_id: DatasetId
    rna: Annotated[str, Field(min_length=1, max_length=32)]
    modification: Annotated[str, Field(min_length=1, max_length=255)]
    tech: Annotated[str, Field(min_length=1, max_length=255)]
    cto: Annotated[str, Field(min_length=1, max_length=255)]
    short_label: Annotated[
        str, Field(min_length=1, max_length=17, pattern=r"[a-zA-Z0-9 ]")
    ]
    long_label: Annotated[
        str, Field(min_length=1, max_length=76, pattern=r"[a-zA-Z0-9 ]")
    ]
    hub_root: Path
    hub_dir: Path
    tmp_dir: Path


class Subtrack(BaseModel):
    """Subtrack."""

    spec: SubtrackSpec
    records: Iterable[EufRecord]


class TrackDbTrack(BaseModel):
    """TrackDb track."""

    name: Annotated[
        str, Field(pattern=r"[a-zA-Z0-9_-]")
    ]  # Name of the dataset (unique).
    short_label: Annotated[
        str, Field(min_length=1, max_length=17, pattern=r"[a-zA-Z0-9 ]")
    ]
    long_label: Annotated[
        str, Field(min_length=1, max_length=76, pattern=r"[a-zA-Z0-9 ]")
    ]
    big_data_url: str  # Full URL or relative to trackDb.
    parent: Annotated[str, Field(pattern=r"[a-zA-Z0-9_-]")]
    mouse_over: str = (
        "$name | score: $score | coverage: $coverage | percent modified: $frequency"
    )
    track_type: str = "bigBed 9+2"
    item_rgb: str = "on"  # Activate item coloring using itemRgb.
    use_score: int = 0  # Turn off score-based shading and filtering.
    no_score_filter: str = "on"
    spectrum: str = "off"

    def render(self) -> str:
        lines = [
            f"track {self.name}",
            f"type {self.track_type}",
            f"parent {self.parent} off",
            f"bigDataUrl {self.big_data_url}",
            f"shortLabel {self.short_label}",
            f"longLabel {self.long_label}",
            f"mouseOver {self.mouse_over}",
            f"itemRgb {self.item_rgb}",
            f"useScore {self.use_score}",
            f"noScoreFilter {self.no_score_filter}",
            f"spectrum {self.spectrum}",
            "",
        ]
        return "\n".join(lines)


class FacetedComposite(BaseModel):
    """TrackDb (faceted composite)."""

    name: Annotated[str, Field(pattern=r"[a-zA-Z0-9]")]
    short_label: Annotated[
        str, Field(min_length=1, max_length=17, pattern=r"[a-zA-Z0-9 ]")
    ]
    long_label: Annotated[
        str, Field(min_length=1, max_length=76, pattern=r"[a-zA-Z0-9 ]")
    ]
    track_type: str = "bigBed 9+2"
    meta_data_url: str  # The tsv file with facet information.
    primary_key: Annotated[
        str, Field(pattern=r"[a-zA-Z0-9_-]")
    ]  # Works in tandem with the metaDataUrl setting.
    mode: str = "faceted"
    max_check_boxes: int
    all_button_pair: bool = True
    center_labels: bool = True
    drag_and_drop: bool = True
    hide_empty: bool = True
    tracks: tuple[TrackDbTrack, ...]

    def render(self) -> str:
        lines = [
            f"track {self.name}",
            f"shortLabel {self.short_label}",
            f"longLabel {self.long_label}",
            f"type {self.track_type}",
            f"metaDataUrl {self.meta_data_url}",
            f"primaryKey {self.primary_key}",
            # "compositeTrack on",
            f"compositeTrack {self.mode}",
            f"maxCheckBoxes {self.max_check_boxes}",
        ]
        if self.all_button_pair:
            lines.append("allButtonPair on")
        if self.center_labels:
            lines.append("centerLabelsDense on")
        if self.drag_and_drop:
            lines.append("dragAndDrop subTracks")
        if self.hide_empty:
            lines.append("hideEmptySubtracks on")
        lines.append("")
        for tr in self.tracks:
            lines.append(tr.render().rstrip())
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


# autosql


class AutoSqlField(BaseModel):
    """Autosql field."""

    astype: str
    name: str
    description: str


class AutoSqlSchema(BaseModel):
    """Autosql schema."""

    table: str
    title: str
    fields: tuple[AutoSqlField, ...]

    def render(self) -> str:
        lines = [f"table {self.table}", f'"{self.title}"', "("]
        for field in self.fields:
            lines.append(f'{field.astype}\t{field.name};\t"{field.description}"')
        lines.append(")")
        return "\n".join(lines) + "\n"
