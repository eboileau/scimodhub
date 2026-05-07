from scimodhub.api import get_request


def test_get_request():
    version = "v0"
    assert (
        get_request(version, "chroms", parts="9606")
        == "https://scimodom.dieterichlab.org/api/v0/chroms/9606"
    )
    assert (
        get_request(version, "dataset")
        == "https://scimodom.dieterichlab.org/api/v0/dataset/list_all"
    )
    assert (
        get_request(version, "download", parts="JBTYPMm6qNsy")
        == "https://scimodom.dieterichlab.org/api/v0/transfer/dataset/JBTYPMm6qNsy"
    )
