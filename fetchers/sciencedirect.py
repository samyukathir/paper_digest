"""ScienceDirect fetcher via the Elsevier Developer API. Requires a free
API key from https://dev.elsevier.com/ — set sources.sciencedirect.enabled:
true in config.yaml and ELSEVIER_API_KEY in your .env once you have one.

LIMITATION: without an institutional subscription, Elsevier's API only
returns metadata (title, authors, DOI, link) — not full abstracts — for
most requests. Papers from this source may show a thin/empty summary;
the digest step falls back to the title in that case."""
import os
from datetime import date

import requests

SEARCH_URL = "https://api.elsevier.com/content/search/sciencedirect"


def fetch(cfg, lookback_days):
    api_key = os.environ.get(cfg.get("api_key_env", "ELSEVIER_API_KEY"), "")
    if not api_key:
        return []

    query = cfg.get("query", "")
    max_results = cfg.get("max_results", 40)
    year = date.today().year

    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    params = {
        "query": query,
        "date": str(year),
        "count": min(max_results, 100),
        "sort": "-date",
    }
    try:
        resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    papers = []
    for item in resp.json().get("search-results", {}).get("entry", []):
        title = item.get("dc:title", "")
        if not title:
            continue
        link = ""
        for l in item.get("link", []):
            if l.get("@ref") == "scidir":
                link = l.get("@href", "")
                break
        doi = item.get("prism:doi", "")
        papers.append({
            "id": f"sciencedirect:{doi or link or title}",
            "title": " ".join(title.split()),
            "summary": " ".join((item.get("dc:description") or "").split()),
            "authors": [item.get("dc:creator", "")] if item.get("dc:creator") else [],
            "link": link or (f"https://doi.org/{doi}" if doi else ""),
            "published": item.get("prism:coverDate", ""),
            "source": "sciencedirect",
        })
    return papers
