from io import StringIO
from pathlib import Path

from scimodhub.utils import (
    load_metadata,
    frequency_to_rgb_triplet,
    get_tmp_dir,
    get_hub_dir,
    get_chrom_mapping,
    get_type,
)
from scimodhub.models import MetadataRow, TrackDb, TrackHubConfig


METADATA_TBL = """project_id\tdataset_id\ttaxa_id\trna\tmodomics_sname\ttech\tcto\tbedrmod_path
WrBiNJCZ\ta7o5Kmjr4Tdp\t9606\tWTS\tm6A,Y\tpsi-co-mAFiA\tHEK293T\tpath"""

EXPECTED_TBL = [
    MetadataRow(
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
]

CONFIG = {
    "working_dir": "working",
    "staging_dir": "staging",
    "genomes": {
        "h_sapiens": {
            "taxa_id": 9606,
            "assembly": {"GRCh38": "hg38"},
            "chroms": {"mapping": "path/to/mapping.tsv", "sizes": None},
            "label": "H. sapiens",
        },
    },
    "hub": {"hub": {"name": "MyHub"}},
}

CHROM_TBL = """1\tchr1\n2\tchr2"""

EXPECTED_DICT = {"1": "chr1", "2": "chr2"}

TRACKDB = TrackDb(
    name="trackDbName",
    short_label="trackDb (label)",
    long_label="trackDb long label (label)",
)

HUB_CONFIG = TrackHubConfig(
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


def test_load_metadata():
    assembly = "GRCh38"
    rows = load_metadata(StringIO(METADATA_TBL), assembly)
    assert rows[0] == EXPECTED_TBL[0]
    assert len(rows) == 1


def test_frequency_to_rgb_triplet():
    triplet = frequency_to_rgb_triplet(25.5)
    assert triplet == "66,0,189"


def test_get_tmp_dir():
    tmp_dir = get_tmp_dir(CONFIG, "h_sapiens")
    assert tmp_dir == Path("working", "hsapiens", "hg38")


def test_get_hub_dir():
    hub_dir = get_hub_dir(CONFIG, "h_sapiens")
    assert hub_dir == Path("staging", "MyHub", "hsapiens", "hg38")
    hub_dir = get_hub_dir(CONFIG)
    assert hub_dir == Path("staging", "MyHub")


def test_get_chrom_mapping():
    d = get_chrom_mapping(StringIO(CHROM_TBL))
    assert d == EXPECTED_DICT


def test_get_type():
    bed_type = get_type(HUB_CONFIG)
    assert bed_type == "9 + 2"
    hub_cfg = HUB_CONFIG.model_copy()
    hub_cfg.score_policy = "zero"
    bed_type = get_type(hub_cfg)
    assert bed_type == "9 + 3"
