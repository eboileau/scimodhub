from pathlib import Path

from scimodhub.bigbed import (
    _write_bed,
    _write_autosql,
    _sort_bed,
    _convert_to_bigbed,
)
from scimodhub.models import Hub, TrackDb, TrackHubConfig, EufRecord

from tests.mocks.io import MockStringIO


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


RECORDS = [
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


EXPECTED_BED = """chr1\t102\t103\tm6A\t10\t+\t102\t103\t204,0,51\t50\t80
chr1\t105\t106\tY\t20\t+\t105\t106\t128,0,128\t20\t50
"""


EXPECTED_BED_ZERO = """chr1\t102\t103\tm6A\t0\t+\t102\t103\t204,0,51\t50\t80\t10
chr1\t105\t106\tY\t0\t+\t105\t106\t128,0,128\t20\t50\t20
"""


DEFAULT_SCHEMA = """table bedRMod
"bigRMod bedRMod"
(
string\tchrom;\t"Chromosome"
uint\tchromStart;\t"Modification start position"
uint\tchromEnd;\t"Modification end position"
string\tname;\t"Modification short name"
uint\tscore;\t"bedRMod score or 0; off"
char[1]\tstrand;\t"Strand"
uint\tthickStart;\t"Thick start"
uint\tthickEnd;\t"Thick end"
string\titemRgb;\t"Blue (0) to red (100) percent modified"
uint\tcoverage;\t"Coverage"
float\tfrequency;\t"Percent modified"
)
"""


ZERO_SCHEMA = """table bedRMod
"bigRMod bedRMod"
(
string\tchrom;\t"Chromosome"
uint\tchromStart;\t"Modification start position"
uint\tchromEnd;\t"Modification end position"
string\tname;\t"Modification short name"
uint\tscore;\t"bedRMod score or 0; off"
char[1]\tstrand;\t"Strand"
uint\tthickStart;\t"Thick start"
uint\tthickEnd;\t"Thick end"
string\titemRgb;\t"Blue (0) to red (100) percent modified"
uint\tcoverage;\t"Coverage"
float\tfrequency;\t"Percent modified"
uint\trawScore;\t"bedRmod score"
)
"""


DICT = {"1": "chr1", "2": "chr2"}


def _generate_records():
    for record in RECORDS:
        yield record


def _mock_run(cmd, caller):
    print(cmd)


def test_write_bed():
    with MockStringIO() as fh:
        _write_bed(fh, HUB_CONFIG, DICT, _generate_records())
    assert fh.final_content == EXPECTED_BED
    hub_cfg = HUB_CONFIG.model_copy()
    hub_cfg.score_policy = "zero"
    with MockStringIO() as fh:
        _write_bed(fh, hub_cfg, DICT, _generate_records())
    assert fh.final_content == EXPECTED_BED_ZERO


def test_write_autosql():
    with MockStringIO() as fh:
        _write_autosql(fh, HUB_CONFIG)
    assert fh.final_content == DEFAULT_SCHEMA
    hub_cfg = HUB_CONFIG.model_copy()
    hub_cfg.score_policy = "zero"
    with MockStringIO() as fh:
        _write_autosql(fh, hub_cfg)
    assert fh.final_content == ZERO_SCHEMA


def test_sort_bed(mocker, capsys):
    mock_run = mocker.patch("scimodhub.bigbed._run")
    mock_run.side_effect = _mock_run
    _sort_bed("bed", "sorted")
    captured = capsys.readouterr()
    assert captured.out == "sort -k1,1 -k2,2n bed > sorted\n"
    mock_run.assert_called_once()


def test_convert_to_bigbed(mocker, capsys):
    mock_run = mocker.patch("scimodhub.bigbed._run")
    mock_run.side_effect = _mock_run
    _convert_to_bigbed("sorted", "chrom.sizes", "autosql", "bigbed", "9+5")
    captured = capsys.readouterr()
    assert (
        captured.out
        == "bedToBigBed -tab -as=autosql -type=bed9+5 sorted chrom.sizes bigbed\n"
    )
    mock_run.assert_called_once()
