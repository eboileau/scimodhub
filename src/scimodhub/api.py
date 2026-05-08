from urllib.parse import urlparse, urlunparse, urlencode, urljoin


GITHUB_REST = "https://api.github.com/repos/"
SCIMODOM_REST = "https://scimodom.dieterichlab.org/"
SCIMODOM_ENDPOINTS = {
    "v0": {
        "chroms": "api/v0/chroms/",
        "dataset": "api/v0/dataset/list_all",
        "download": "api/v0/transfer/dataset/",
        "modomics": "api/v0/modomics",
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
    path = urljoin(SCIMODOM_ENDPOINTS[version][endpoint], parts)
    return _get_url(SCIMODOM_REST, path, query)
