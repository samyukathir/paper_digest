"""Semantic Scholar fetcher via the Graph API. Free; an optional API key
(set via env var named in config) raises the rate limit."""
import os
from datetime import date, timedelta

import requests

SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,authors,url,publicationDate,externalIds"


def fetch(cfg, lookback_days):
    query = cfg.get("query", "")
    max_results = cfg.get("max_results", 60)
    api_key = os.environ.get(cfg.get("api_key_env", ""), "") if cfg.get("api_key_env") else ""

    end = date.today()
    start = end - timedelta(days=lookback_days)
    date_range = f"{start.isoformat()}:{end.isoformat()}"

    params = {
        "query": query,
        "fields": FIELDS,
        "limit": min(max_results, 100),
        "publicationDateOrYear": date_range,
    }
    headers = {"x-api-key": api_key} if api_key else {}

    try:
        resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    papers = []
    for item in resp.json().get("data", []):
        if not item.get("abstract"):
            continue
        papers.append({
            "id": f"s2:{item.get('paperId')}",
            "title": " ".join((item.get("title") or "").split()),
            "summary": " ".join((item.get("abstract") or "").split()),
            "authors": [a.get("name", "") for a in item.get("authors", [])],
            "link": item.get("url") or f"https://www.semanticscholar.org/paper/{item.get('paperId')}",
            "published": item.get("publicationDate") or "",
            "source": "semantic_scholar",
        })
    return papers
