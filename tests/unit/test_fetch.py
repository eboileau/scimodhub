from pathlib import Path

import pytest
import requests

from scimodhub.models import MetadataRow
from scimodhub.fetch import (
    _write_metadata,
    _overwrite_metadata,
    _write_chroms,
    _get_dataset,
    _update_rows,
)
from scimodhub.utils import EmptyDataError
from tests.mocks.io import MockStringIO


CHROM_SIZES = "chr1\t248956422\nchr2\t242193529\n"

METADATA_TBL = """dataset_id\tproject_id\ttaxa_id\tassembly\trna\tmodomics_sname\ttech\tcto\tbedrmod_path
3XXcptjDwfaK\t49mrpvBp\t9606\tGRCh38\tWTS\tm5C,Y\tm5C-TAC-seq\tHEK293T\tpath
"""

TBL = [
    MetadataRow(
        dataset_id="3XXcptjDwfaK",
        project_id="49mrpvBp",
        taxa_id=9606,
        assembly="GRCh38",
        rna="WTS",
        modomics_sname="m5C,Y",
        tech="m5C-TAC-seq",
        cto="HEK293T",
        bedrmod_path=Path("path"),
    ),
    MetadataRow(
        dataset_id="3XXcptjDwfaK",
        project_id="49mrpvBp",
        taxa_id=9606,
        assembly="GRCh38",
        rna="WTS",
        modomics_sname="m5C,Y",
        tech="m5C-TAC-seq",
        cto="HEK293T",
        bedrmod_path=Path("data_dir/3XXcptjDwfaK.bed"),
    ),
]


def test_write_chroms(mocker):
    mock_get = mocker.patch("scimodhub.fetch.requests.get")
    response = mock_get.return_value
    response.status_code = 200
    response.json.return_value = [
        {"chrom": "1", "size": 248956422},
        {"chrom": "2", "size": 242193529},
    ]
    with MockStringIO() as fh:
        _write_chroms(fh, "v0", 9606, {"1": "chr1", "2": "chr2"})
    assert fh.final_content == CHROM_SIZES


def test_write_metadata(mocker):
    mock_get = mocker.patch("scimodhub.fetch.requests.get")
    response = mock_get.return_value
    response.status_code = 200
    response.json.return_value = [
        {
            "cto": "HEK293T",
            "dataset_id": "3XXcptjDwfaK",
            "modomics_sname": "m5C,Y",
            "pmid": "39002544",
            "project_id": "49mrpvBp",
            "rna": "WTS",
            "taxa_id": 9606,
            "taxa_sname": "H. sapiens",
            "tech": "m5C-TAC-seq",
        },
        {
            "cto": "mESC",
            "dataset_id": "4Pw4rPAuDNwd",
            "modomics_sname": "m5C",
            "pmid": "39002544",
            "project_id": "49mrpvBp",
            "rna": "WTS",
            "taxa_id": 10090,
            "taxa_sname": "M. musculus",
            "tech": "m5C-TAC-seq",
        },
    ]
    tbl = METADATA_TBL.replace("\tbedrmod_path", "")
    tbl = tbl.replace("\tpath", "")
    with MockStringIO() as fh:
        _write_metadata(fh, "v0", 9606, "GRCh38", [])
    assert fh.final_content == tbl

    with MockStringIO() as fh:
        _write_metadata(fh, "v0", 9606, "GRCh38", ["3XXcptjDwfaK"])
    assert fh.final_content == tbl

    with pytest.raises(EmptyDataError) as exc:
        with MockStringIO() as fh:
            _write_metadata(fh, "v0", 9606, "GRCh38", ["4Pw4rPAuDNwd"])
    assert (str(exc.value)) == "No EUFIDs/organism match this request."


def test_overwrite_metadata():
    with MockStringIO() as fh:
        _overwrite_metadata(fh, TBL[:-1])
    assert fh.final_content == METADATA_TBL


def test_update_rows(mocker, caplog):
    mock_get_dataset = mocker.patch("scimodhub.fetch._get_dataset")
    mock_get_dataset.return_value = None
    rows = _update_rows(TBL[:-1], "data_dir", "vO")
    assert rows[0] == TBL[1]
    assert len(rows) == 1

    mock_get_dataset = mocker.patch("scimodhub.fetch._get_dataset")
    mock_get_dataset.side_effect = requests.exceptions.ConnectTimeout("Mock error.")
    rows = _update_rows(TBL[:-1], "data_dir", "vO")
    assert caplog.messages == ["Download: Skipping 3XXcptjDwfaK: Mock error."]
    assert len(rows) == 0
