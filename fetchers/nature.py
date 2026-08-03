"""Nature (and other Springer Nature journals) fetcher via the free
Springer Nature Metadata API. Requires a free API key from
https://dev.springernature.com/ — set sources.nature.enabled: true in
config.yaml and SPRINGER_NATURE_API_KEY in your .env once you have one."""
import os
from datetime import date, timedelta

import requests

BASE_URL = "http://api.springernature.com/meta/v2/json"


def fetch(cfg, lookback_days):
    api_key = os.environ.get(cfg.get("api_key_env", "SPRINGER_NATURE_API_KEY"), "")
    if not api_key:
        return []

    query = cfg.get("query", "")
    max_results = cfg.get("max_results", 40)

    end = date.today()
    start = end - timedelta(days=lookback_days)
    date_filter = f'onlinedatefrom:{start.isoformat()} onlinedateto:{end.isoformat()}'
    full_query = f"({query}) {date_filter}" if query else date_filter

    params = {
        "q": full_query,
        "api_key": api_key,
        "p": min(max_results, 100),
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    papers = []
    for item in resp.json().get("records", []):
        abstract = item.get("abstract", "")
        if not abstract:
            continue
        urls = item.get("url", [])
        link = urls[0].get("value") if urls else f"https://doi.org/{item.get('doi', '')}"
        papers.append({
            "id": f"nature:{item.get('identifier')}",
            "title": " ".join((item.get("title") or "").split()),
            "summary": " ".join(abstract.split()),
            "authors": [c.get("creator", "") for c in item.get("creators", [])],
            "link": link,
            "published": item.get("publicationDate", ""),
            "source": "nature",
        })
    return papers
