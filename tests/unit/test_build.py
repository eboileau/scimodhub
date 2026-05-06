from pathlib import Path

import pytest

from scimodhub.build import _get_records, _validate_header, _add_subtrack_spec
from scimodhub.models import (
    Hub,
    TrackDb,
    TrackHubConfig,
    MetadataRow,
    EufRecord,
    SubtrackSpec,
)


HUB = Hub(
    name="myhub",
    short_label="short",
    long_label="longer label",
    email="email@uni-heidelberg.de",
)

TRACKDB = TrackDb(
    name="trackDbName",
    short_label="trackDb (label)",
    long_label="trackDb long label (label)",
)

HUB_CONFIG = TrackHubConfig(
    hub=HUB,
    track_db=TRACKDB,
    score_policy="preserve",
    max_check_boxes=20,
    hide_empty=True,
    center_labels=True,
    all_button_pair=True,
    drag_and_drop=True,
    rgb_min=(0, 0, 255),
    rgb_max=(255, 0, 0),
)


METADATA_ROW = MetadataRow(
    dataset_id="a7o5Kmjr4Tdp",
    project_id="WrBiNJCZ",
    taxa_id=9606,
    assembly="GRCh38",
    rna="WTS",
    modomics_sname="m6A,Y",
    tech="psi-co-mAFiA",
    cto="HEK293T",
    bedrmod_path=Path("path"),
)


EXPECTED_SUBTRACK_SPEC = SubtrackSpec(
    primary_key="a7o5Kmjr4TdpY",
    subtrack="trackDbName_a7o5Kmjr4TdpY",
    dataset_id="a7o5Kmjr4Tdp",
    rna="WTS",
    modification="Y",
    tech="psi-co-mAFiA",
    cto="HEK293T",
    short_label="Y",
    long_label="EUFID:a7o5Kmjr4Tdp | Y HEK293T psi-co-mAFiA",
    hub_root=Path("staging/myHub"),
    hub_dir=Path("staging/myHub/hsapiens/hg38"),
    tmp_dir=Path("work/hsapiens/hg38"),
)


class MockEufImporter:
    RESULT = [
        EufRecord(
            chrom="1",
            start=102,
            end=103,
            name="m6A",
            score=10,
            strand="+",
            thick_start=102,
            thick_end=103,
            item_rgb="0,0,0",
            coverage=50,
            frequency=80,
        ),
        EufRecord(
            chrom="1",
            start=105,
            end=106,
            name="Y",
            score=20,
            strand="+",
            thick_start=105,
            thick_end=106,
            item_rgb="0,0,0",
            coverage=20,
            frequency=50,
        ),
    ]

    def __init__(self):
        self._headers: dict[str, str] = {
            "fileformat": "bedRModv1.8",
            "assembly": "GRCh38",
        }

    def get_header(self, name):
        if name in self._headers:
            return self._headers[name]
        else:
            return None

    @staticmethod
    def parse():
        for x in MockEufImporter.RESULT:
            yield x


def test_get_records():
    importer = MockEufImporter()
    records = _get_records(importer.RESULT, "Y")
    record = next(records)
    assert record == importer.RESULT[1]
    with pytest.raises(StopIteration):
        next(records)


def test_validate_header():
    importer = MockEufImporter()
    assembly = "GRCh38"
    euf_versions = ["1.8"]
    assert _validate_header(importer, "dataset_id", assembly, euf_versions) is None


def test_add_subtrack_spec():
    spec = _add_subtrack_spec(
        METADATA_ROW,
        HUB_CONFIG,
        "Y",
        Path("staging", "myHub"),
        Path("staging", "myHub", "hsapiens", "hg38"),
        Path("work", "hsapiens", "hg38"),
    )
    assert spec == EXPECTED_SUBTRACK_SPEC
