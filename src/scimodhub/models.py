from typing import Annotated, Self, Iterable
from datetime import date
from pydantic import BaseModel, Field, EmailStr, model_validator
from pathlib import Path

# defaults

FilterSettings = {
    "frequency": (
        "filter.frequency 0\n"
        "filterByRange.frequency on\n"
        "filterLimits.frequency 0:100\n"
        "filterLabel.frequency Frequency (percent modified)"
    ),
    "coverage": (
        "filter.coverage 0\n"
        "filterLimits.coverage 0:400000\n"
        "filterLabel.coverage Minimum coverage"
    ),
}


# metadata

ProjectId = Annotated[str, Field(min_length=8, max_length=8)]
DatasetId = Annotated[str, Field(min_length=12, max_length=12)]


class MetadataRow(BaseModel):
    """Metadata."""

    dataset_id: DatasetId
    project_id: ProjectId
    dataset_title: Annotated[str, Field(min_length=1, max_length=255)]
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
    description: Path
    image: Path | None = None
    public_address: str | None = None


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
    score_display: bool
    max_check_boxes: int
    hide_empty: bool
    center_labels: bool
    default_sort_field: str
    filters: list[str] | None = None
    toggle_on: dict[str, list[str]] | None = None
    rgb_min: tuple[int, int, int]
    rgb_max: tuple[int, int, int]


class SubtrackSpec(BaseModel):
    """Subtrack metadata."""

    primary_key: Annotated[str, Field(pattern=r"[a-zA-Z0-9_-]")]
    subtrack: Annotated[str, Field(pattern=r"[a-zA-Z0-9_-]")]
    toggle_on: str = "off"
    dataset_id: DatasetId
    dataset_title: Annotated[str, Field(min_length=1, max_length=255)]
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
    parent: Annotated[str, Field(pattern=r"[a-zA-Z0-9_-]")]
    toggle_on: str = "off"
    short_label: Annotated[
        str, Field(min_length=1, max_length=17, pattern=r"[a-zA-Z0-9 ]")
    ]
    long_label: Annotated[
        str, Field(min_length=1, max_length=76, pattern=r"[a-zA-Z0-9 ]")
    ]
    big_data_url: str  # Full URL or relative to trackDb.
    url: str
    url_label: str

    def render(self) -> str:
        lines = [
            f"    track {self.name}",
            f"    parent {self.parent} {self.toggle_on}",
            f"    shortLabel {self.short_label}",
            f"    longLabel {self.long_label}",
            f"    bigDataUrl {self.big_data_url}",
            f"    url {self.url}",
            f"    urlLabel {self.url_label}",
            "",
        ]
        return "\n".join(lines)


class FacetedComposite(BaseModel):
    """TrackDb (faceted composite container)."""

    name: Annotated[str, Field(pattern=r"[a-zA-Z0-9]")]
    short_label: Annotated[
        str, Field(min_length=1, max_length=17, pattern=r"[a-zA-Z0-9 ]")
    ]
    long_label: Annotated[
        str, Field(min_length=1, max_length=76, pattern=r"[a-zA-Z0-9 ]")
    ]
    track_type: str = "bigBed 9+2"
    mode: str = "faceted"
    visibility: str = "pack"
    meta_data_url: str  # The tsv file with facet information.
    primary_key: Annotated[
        str, Field(pattern=r"[a-zA-Z0-9_-]")
    ]  # Works in tandem with the metaDataUrl setting.
    max_check_boxes: int
    default_sort_field: str
    center_labels: bool = True
    hide_empty: bool = True
    date: date
    version: str
    create_index: bool = False
    item_rgb: str = "on"  # Activate item coloring using itemRgb.
    mouse_over: str
    filters: list[str] | None
    tracks: tuple[TrackDbTrack, ...]

    def render(self) -> str:
        lines = [
            f"track {self.name}",
            f"shortLabel {self.short_label}",
            f"longLabel {self.long_label}",
            f"type {self.track_type}",
            f"compositeTrack {self.mode}",
            f"visibility {self.visibility}",
            f"html {self.name}",
            f"metaDataUrl {self.meta_data_url}",
            f"primaryKey {self.primary_key}",
            "subtrackUrls _eufid=https://scimodom.dieterichlab.org/browse/$$",
            f"defaultSortField {self.default_sort_field}",
            f"dataVersion Sci-ModoM {self.version} {self.date}",
            f"itemRgb {self.item_rgb}",
            f"mouseOver {self.mouse_over}",
            f"maxCheckboxes {self.max_check_boxes}",
        ]
        if self.center_labels:
            lines.append("centerLabelsDense on")
        if self.hide_empty:
            lines.append("hideEmptySubtracks on")
        if self.create_index:
            lines.append(f"hideEmptySubtracksMultiBedUrl {self.name}.multiBed.bb")
            lines.append(
                f"hideEmptySubtracksSourcesUrl {self.name}.multiBedSources.tab"
            )
        if self.filters:
            for filter in self.filters:
                lines.append(FilterSettings[filter])
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
