from urllib.parse import urlparse, urlunparse, urlencode, urljoin


GITHUB_REST = "https://api.github.com/repos/"
MODOMICS_REST = "https://www.genesilico.pl/modomics/api/"
SCIMODOM_REST = "https://scimodom.dieterichlab.org/api/{version}/".format
SCIMODOM_ENDPOINTS = {
    "v0": {
        "chroms": "chroms/",
        "dataset": "dataset/list_all/",
        "download": "transfer/dataset/",
    },
}


def _get_url(base_url: str, path: str, query: dict[str, str | int]) -> str:
    parse_results = urlparse(base_url, allow_fragments=False)
    parse_results = parse_results._replace(path=path)
    parse_results = parse_results._replace(params=urlencode(query))
    return urlunparse(parse_results)


def get_request(
    version: str,
    endpoint: str,
    parts: str = "",
    query: dict[str, str | int] = dict(),
) -> str:
    """Get API URL for a given endpoint."""
    base_url = SCIMODOM_REST(version=version)
    path = urljoin(SCIMODOM_ENDPOINTS[version][endpoint], parts)
    return _get_url(base_url, path, query)
