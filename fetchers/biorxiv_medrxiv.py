"""bioRxiv / medRxiv fetcher via the public api.biorxiv.org details endpoint.
Free, no key required. Docs: https://api.biorxiv.org/"""
from datetime import date, timedelta

import requests

BASE_URL = "https://api.biorxiv.org/details"


def _fetch_server(server, start, end, max_results):
    papers = []
    cursor = 0
    while len(papers) < max_results:
        url = f"{BASE_URL}/{server}/{start}/{end}/{cursor}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        collection = data.get("collection", [])
        if not collection:
            break
        for item in collection:
            papers.append({
                "id": f"{server}:{item.get('doi')}",
                "title": " ".join(item.get("title", "").split()),
                "summary": " ".join(item.get("abstract", "").split()),
                "authors": [a.strip() for a in item.get("authors", "").split(";") if a.strip()],
                "link": f"https://doi.org/{item.get('doi')}",
                "published": item.get("date", ""),
                "source": server,
            })
            if len(papers) >= max_results:
                break
        cursor += len(collection)
        if len(collection) < 100:  # API pages in chunks of 100; short page == done
            break
    return papers


def fetch(cfg, lookback_days):
    servers = cfg.get("servers", ["biorxiv", "medrxiv"])
    max_results = cfg.get("max_results", 100)
    per_server = max(1, max_results // max(1, len(servers)))

    end = date.today()
    start = end - timedelta(days=lookback_days)

    papers = []
    for server in servers:
        try:
            papers.extend(_fetch_server(server, start.isoformat(), end.isoformat(), per_server))
        except requests.RequestException:
            continue
    return papers
