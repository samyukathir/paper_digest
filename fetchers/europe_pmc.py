"""Europe PMC fetcher. Free REST API, no key required."""
from datetime import date, timedelta

import requests

SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def fetch(cfg, lookback_days):
    query = cfg.get("query", "")
    max_results = cfg.get("max_results", 60)

    end = date.today()
    start = end - timedelta(days=lookback_days)
    date_filter = f"FIRST_PDATE:[{start.isoformat()} TO {end.isoformat()}]"
    full_query = f"({query}) AND {date_filter}" if query else date_filter

    params = {
        "query": full_query,
        "format": "json",
        "resultType": "core",
        "pageSize": min(max_results, 100),
        "sort": "P_PDATE_D desc",
    }
    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    papers = []
    for item in resp.json().get("resultList", {}).get("result", []):
        abstract = item.get("abstractText", "")
        if not abstract:
            continue
        doi = item.get("doi")
        link = f"https://doi.org/{doi}" if doi else f"https://europepmc.org/article/{item.get('source')}/{item.get('id')}"
        papers.append({
            "id": f"epmc:{item.get('id')}",
            "title": " ".join(item.get("title", "").split()),
            "summary": " ".join(abstract.split()),
            "authors": [a.strip() for a in item.get("authorString", "").split(",") if a.strip()],
            "link": link,
            "published": item.get("firstPublicationDate", ""),
            "source": "europe_pmc",
        })
    return papers
