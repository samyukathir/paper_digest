"""OpenAlex fetcher. Free, no key required; supplying an email via
mailto puts requests in OpenAlex's faster 'polite pool'."""
import os
from datetime import date, timedelta

import requests

BASE_URL = "https://api.openalex.org/works"


def _reconstruct_abstract(inverted_index):
    if not inverted_index:
        return ""
    positions = {}
    for word, idxs in inverted_index.items():
        for idx in idxs:
            positions[idx] = word
    return " ".join(positions[i] for i in sorted(positions))


def fetch(cfg, lookback_days):
    query = cfg.get("query", "")
    max_results = cfg.get("max_results", 60)
    mailto = os.environ.get(cfg.get("mailto_env", ""), "") if cfg.get("mailto_env") else ""

    end = date.today()
    start = end - timedelta(days=lookback_days)

    params = {
        "search": query,
        "filter": f"from_publication_date:{start.isoformat()},to_publication_date:{end.isoformat()}",
        "sort": "publication_date:desc",
        "per-page": min(max_results, 100),
    }
    if mailto:
        params["mailto"] = mailto

    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    papers = []
    for item in resp.json().get("results", []):
        abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))
        if not abstract:
            continue
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in item.get("authorships", [])
        ]
        link = item.get("doi") or item.get("id")
        papers.append({
            "id": f"openalex:{item.get('id')}",
            "title": " ".join((item.get("title") or "").split()),
            "summary": " ".join(abstract.split()),
            "authors": authors,
            "link": link,
            "published": item.get("publication_date", ""),
            "source": "openalex",
        })
    return papers
