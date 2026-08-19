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
            "description": "description.html",
            "image": None,
            "public_address": None,
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
    description=Path("description.html"),
)

EXPECTED_TRACKDB = TrackDb(
    name="trackDbName",
    short_label="trackDb (label)",
    long_label="trackDb long label (label)",
)

EXPECTED_TRACKDB_NO_LABEL = TrackDb(
    name="trackDbName",
    short_label="trackDb",
    long_label="trackDb long label",
)

EXPECTED_HUB_CONFIG = TrackHubConfig(
    track_db=EXPECTED_TRACKDB,
    score_policy="preserve",
    score_display=True,
    max_check_boxes=20,
    hide_empty=True,
    center_labels=True,
    default_sort_field="modification",
    rgb_min=(0, 0, 255),
    rgb_max=(255, 0, 0),
)

SUBTRACK_SPEC = SubtrackSpec(
    primary_key="a7o5Kmjr4TdpY",
    subtrack="trackDbName_a7o5Kmjr4TdpY",
    dataset_id="a7o5Kmjr4Tdp",
    dataset_title="HEK293T Trub1-KD",
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

EXPECTED_METADATA = """dataset\t_eufid\tmodification\tbiosample\ttechnology
a7o5Kmjr4TdpY|HEK293T Trub1-KD\ta7o5Kmjr4Tdp\tY\tHEK293T\tpsi-co-mAFiA
"""

EXPECTED_TRACK_HUB = {
    "hub.txt": "hub myHub\nshortLabel short\nlongLabel longer label\ngenomesFile genomes.txt\nemail email@uni-heidelberg.de\ndescriptionUrl description.html\n",
    "genomes.txt": "genome hg38\ntrackDb hsapiens/hg38/trackDb.txt\n\ngenome mm39\ntrackDb mmusculus/mm39/trackDb.txt\n\n",
    "description.html": "html description",
}

EXPECTED_TRACK_DB = "track trackDbName\nshortLabel trackDb (label)\nlongLabel trackDb long label (label) (1 datasets)\ntype bigBed 9 + 2\ncompositeTrack faceted\nvisibility pack\nhtml trackDbName\nmetaDataUrl metadata.tsv\nprimaryKey dataset\nsubtrackUrls _eufid=https://scimodom.dieterichlab.org/browse/$$\ndefaultSortField modification\ndataVersion Sci-ModoM  2026-08-11\nitemRgb on\nmouseOver $name at $chrom:${chromStart} | score: $score | coverage: $coverage | percent modified: $frequency\nmaxCheckboxes 20\ncenterLabelsDense on\nhideEmptySubtracks on\n\n    track trackDbName_a7o5Kmjr4TdpY\n    parent trackDbName off\n    shortLabel Y\n    longLabel EUFID:a7o5Kmjr4Tdp | Y HEK293T psi-co-mAFiA\n    bigDataUrl a7o5Kmjr4TdpY.bb\n    url https://scimodom.dieterichlab.org/browse/a7o5Kmjr4Tdp\n    urlLabel Sci-ModoM dataset record (a7o5Kmjr4Tdp)\n\n"


EXPECTED_TRACK_DB_WITH_INDEX = "track trackDbName\nshortLabel trackDb (label)\nlongLabel trackDb long label (label) (1 datasets)\ntype bigBed 9 + 2\ncompositeTrack faceted\nvisibility pack\nhtml trackDbName\nmetaDataUrl metadata.tsv\nprimaryKey dataset\nsubtrackUrls _eufid=https://scimodom.dieterichlab.org/browse/$$\ndefaultSortField modification\ndataVersion Sci-ModoM  2026-08-11\nitemRgb on\nmouseOver $name at $chrom:${chromStart} | score: $score | coverage: $coverage | percent modified: $frequency\nmaxCheckboxes 20\ncenterLabelsDense on\nhideEmptySubtracks on\nhideEmptySubtracksMultiBedUrl trackDbName.multiBed.bb\nhideEmptySubtracksSourcesUrl trackDbName.multiBedSources.tab\n\n    track trackDbName_a7o5Kmjr4TdpY\n    parent trackDbName off\n    shortLabel Y\n    longLabel EUFID:a7o5Kmjr4Tdp | Y HEK293T psi-co-mAFiA\n    bigDataUrl a7o5Kmjr4TdpY.bb\n    url https://scimodom.dieterichlab.org/browse/a7o5Kmjr4Tdp\n    urlLabel Sci-ModoM dataset record (a7o5Kmjr4Tdp)\n\n"


EXPECTED_TRACK_DB_WITH_OPTIONS = "track trackDbName\nshortLabel trackDb (label)\nlongLabel trackDb long label (label) (1 datasets)\ntype bigBed 9 + 2\ncompositeTrack faceted\nvisibility pack\nhtml trackDbName\nmetaDataUrl metadata.tsv\nprimaryKey dataset\nsubtrackUrls _eufid=https://scimodom.dieterichlab.org/browse/$$\ndefaultSortField modification\ndataVersion Sci-ModoM v4.0.2 2026-08-11\nitemRgb on\nmouseOver $name at $chrom:${chromStart} | score: $score | coverage: $coverage | percent modified: $frequency\nmaxCheckboxes 20\ncenterLabelsDense on\nhideEmptySubtracks on\nfilter.frequency 0\nfilterByRange.frequency on\nfilterLimits.frequency 0:100\nfilterLabel.frequency Frequency (percent modified)\nfilter.coverage 0\nfilterLimits.coverage 0:400000\nfilterLabel.coverage Minimum coverage\n\n    track trackDbName_a7o5Kmjr4TdpY\n    parent trackDbName off\n    shortLabel Y\n    longLabel EUFID:a7o5Kmjr4Tdp | Y HEK293T psi-co-mAFiA\n    bigDataUrl a7o5Kmjr4TdpY.bb\n    url https://scimodom.dieterichlab.org/browse/a7o5Kmjr4Tdp\n    urlLabel Sci-ModoM dataset record (a7o5Kmjr4Tdp)\n\n"


def test_track_db_config_from_dict():
    hub_cfg = track_db_config_from_dict(CONFIG, "label")
    assert hub_cfg == EXPECTED_HUB_CONFIG


def test_track_db_config_from_dict_no_label():
    hub_cfg = track_db_config_from_dict(CONFIG, None)
    assert hub_cfg.track_db == EXPECTED_TRACKDB_NO_LABEL


def test_hub_config_from_dict(mocker):
    mock_exists = mocker.patch("pathlib.Path.exists")
    mock_exists.return_value = True
    hub_cfg = hub_config_from_dict(CONFIG)
    assert hub_cfg == EXPECTED_HUB


def test_write_metadata():
    with MockStringIO() as fh:
        write_metadata(fh, SUBTRACKS)
    assert fh.final_content == EXPECTED_METADATA


def test_write_trackdb(freezer):
    freezer.move_to("2026-08-11")
    with MockStringIO() as fh:
        write_trackdb(fh, SUBTRACKS, EXPECTED_HUB_CONFIG, "")
    assert fh.final_content == EXPECTED_TRACK_DB


def test_write_trackdb_with_index(freezer):
    freezer.move_to("2026-08-11")
    with MockStringIO() as fh:
        write_trackdb(fh, SUBTRACKS, EXPECTED_HUB_CONFIG, "", True)
    assert fh.final_content == EXPECTED_TRACK_DB_WITH_INDEX


def test_write_trackdb_with_options(freezer):
    freezer.move_to("2026-08-11")
    HUB_CONFIG = EXPECTED_HUB_CONFIG.model_copy()
    HUB_CONFIG.filters = ["frequency", "coverage"]
    with MockStringIO() as fh:
        write_trackdb(fh, SUBTRACKS, HUB_CONFIG, "v4.0.2")
    assert fh.final_content == EXPECTED_TRACK_DB_WITH_OPTIONS


def test_write_hub_files(mocker):
    mock_read_txt = mocker.patch("pathlib.Path.read_text")
    mock_read_txt.return_value = "html description"
    genomes = [("hg38", "hsapiens/hg38"), ("mm39", "mmusculus/mm39")]
    with ExitStack() as stack:
        files = {
            f: stack.enter_context(MockStringIO())
            for f in ["hub.txt", "genomes.txt", "description.html"]
        }
        write_hub_files(files, EXPECTED_HUB, genomes)
    for k, v in files.items():
        assert v.final_content == EXPECTED_TRACK_HUB[k]


def test_write_hub_description(mocker):
    HUB = EXPECTED_HUB.model_copy()
    HUB.image = Path("path/to/image.png")
    HUB.public_address = "https://public/address"
    mock_read_txt = mocker.patch("pathlib.Path.read_text")
    mock_read_txt.return_value = (
        '<a href="address" target="_blank"><img src="image.png" width="250"></img></a>'
    )
    genomes = [("hg38", "hsapiens/hg38")]
    with ExitStack() as stack:
        files = {
            f: stack.enter_context(MockStringIO())
            for f in ["hub.txt", "genomes.txt", "description.html"]
        }
        write_hub_files(files, HUB, genomes)
    expected_desc = '<a href="address" target="_blank"><img src="https://public/address/image.png" width="250"></img></a>'
    assert files["description.html"].final_content == expected_desc


def test_get_mouse_over():
    mouse_over = _get_mouse_over(EXPECTED_HUB_CONFIG)
    assert mouse_over == (
        "$name at $chrom:${chromStart} | score: $score | coverage: $coverage | percent modified: $frequency"
    )

    hub_cfg = EXPECTED_HUB_CONFIG.model_copy()
    hub_cfg.score_policy = "zero"
    mouse_over = _get_mouse_over(hub_cfg)
    assert mouse_over == (
        "$name at $chrom:${chromStart} | score: $rawScore | "
        "coverage: $coverage | percent modified: $frequency"
    )

    hub_cfg.score_policy = "coverage"
    mouse_over = _get_mouse_over(hub_cfg)
    assert mouse_over == (
        "$name at $chrom:${chromStart} | score: $rawScore | "
        "coverage: $coverage | percent modified: $frequency"
    )

    hub_cfg.score_display = False
    mouse_over = _get_mouse_over(hub_cfg)
    assert mouse_over == (
        "$name at $chrom:${chromStart} | coverage: $coverage | percent modified: $frequency"
    )
