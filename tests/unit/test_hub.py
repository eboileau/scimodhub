from pathlib import Path

from contextlib import ExitStack

from scimodhub.hub import (
    hub_config_from_dict,
    track_db_config_from_dict,
    write_metadata,
    write_trackdb,
    write_hub_files,
    _get_mouse_over,
)
from scimodhub.models import (
    Hub,
    TrackDb,
    TrackHubConfig,
    SubtrackSpec,
    Subtrack,
    EufRecord,
)

from tests.mocks.io import MockStringIO


CONFIG = {
    "hub": {
        "hub": {
            "name": "myHub",
            "short_label": "short",
            "long_label": "longer label",
            "email": "email@uni-heidelberg.de",
        },
        "track_db": {
            "name": "trackDbName",
            "short_label": "trackDb",
            "long_label": "trackDb long label",
        },
    },
}

EXPECTED_HUB = Hub(
    name="myHub",
    short_label="short",
    long_label="longer label",
    email="email@uni-heidelberg.de",
)

EXPECTED_TRACKDB = TrackDb(
    name="trackDbName",
    short_label="trackDb (label)",
    long_label="trackDb long label (label)",
)

EXPECTED_HUB_CONFIG = TrackHubConfig(
    track_db=EXPECTED_TRACKDB,
    score_policy="preserve",
    max_check_boxes=20,
    hide_empty=True,
    center_labels=True,
    all_button_pair=True,
    drag_and_drop=True,
    rgb_min=(0, 0, 255),
    rgb_max=(255, 0, 0),
)

SUBTRACK_SPEC = SubtrackSpec(
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

RECORD = (
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
)

SUBTRACKS = [Subtrack(spec=SUBTRACK_SPEC, records=[RECORD])]

EXPECTED_METADATA = """track\teufid\tmodification\tcellTissueOrganism\ttechnology
a7o5Kmjr4TdpY\ta7o5Kmjr4Tdp\tY\tHEK293T\tpsi-co-mAFiA
"""

EXPECTED_TRACK_HUB = {
    "hub.txt": "hub myHub\nshortLabel short\nlongLabel longer label\ngenomesFile genomes.txt\nemail email@uni-heidelberg.de\ndescriptionUrl description.html\n",
    "genomes.txt": "genome hg38\ntrackDb hsapiens/hg38/trackDb.txt\n\ngenome mm39\ntrackDb mmusculus/mm39/trackDb.txt\n\n",
    "description.html": "<html>\n<head><title>short</title></head>\n<body>\n<h1>longer label</h1>\n<p>This hub uses a faceted composite with one subtrack per dataset x modification.</p>\n<p>Facets are driven by metadata.tsv and can include modification, tissue, technology, and cell type.</p>\n<p>The mouseover text displays coverage, frequency, and score for each item.</p>\n</body>\n</html>\n",
}

EXPECTED_TRACK_DB = "track trackDbName\nshortLabel trackDb (label)\nlongLabel trackDb long label (label)\ntype bigBed 9 + 2\nmetaDataUrl metadata.tsv\nprimaryKey track\ncompositeTrack faceted\nmaxCheckBoxes 20\nallButtonPair on\ncenterLabelsDense on\ndragAndDrop subTracks\nhideEmptySubtracks on\n\ntrack trackDbName_a7o5Kmjr4TdpY\ntype bigBed 9 + 2\nparent trackDbName off\nbigDataUrl a7o5Kmjr4TdpY.bb\nshortLabel Y\nlongLabel EUFID:a7o5Kmjr4Tdp | Y HEK293T psi-co-mAFiA\nmouseOver $name | score: $score | coverage: $coverage | percent modified: $frequency\nitemRgb on\nuseScore 0\nnoScoreFilter on\nspectrum off\n"


def test_track_db_config_from_dict():
    hub_cfg = track_db_config_from_dict(CONFIG, "label")
    assert hub_cfg == EXPECTED_HUB_CONFIG


def test_hub_config_from_dict():
    hub_cfg = hub_config_from_dict(CONFIG)
    assert hub_cfg == EXPECTED_HUB


def test_write_metadata():
    with MockStringIO() as fh:
        write_metadata(fh, SUBTRACKS)
    assert fh.final_content == EXPECTED_METADATA


def test_write_trackdb():
    with MockStringIO() as fh:
        write_trackdb(fh, SUBTRACKS, EXPECTED_HUB_CONFIG)
    assert fh.final_content == EXPECTED_TRACK_DB


def test_write_hub_files():
    genomes = [("hg38", "hsapiens/hg38"), ("mm39", "mmusculus/mm39")]
    with ExitStack() as stack:
        files = {
            f: stack.enter_context(MockStringIO())
            for f in ["hub.txt", "genomes.txt", "description.html"]
        }
        write_hub_files(files, EXPECTED_HUB, genomes)
    for k, v in files.items():
        assert v.final_content == EXPECTED_TRACK_HUB[k]


def test_get_mouse_over():
    mouse_over = _get_mouse_over(EXPECTED_HUB_CONFIG)
    assert mouse_over == (
        "$name | score: $score | coverage: $coverage | percent modified: $frequency"
    )
    hub_cfg = EXPECTED_HUB_CONFIG.model_copy()
    hub_cfg.score_policy = "zero"
    mouse_over = _get_mouse_over(hub_cfg)
    assert mouse_over == (
        "$name | score: $rawScore | "
        "coverage: $coverage | percent modified: $frequency"
    )
