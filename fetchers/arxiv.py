"""arXiv fetcher. Free API, no key required."""
import urllib.parse
import feedparser

BASE_URL = "http://export.arxiv.org/api/query"


def fetch(cfg, lookback_days):
    categories = cfg.get("categories", [])
    max_results = cfg.get("max_results", 100)

    if categories:
        cat_query = "+OR+".join(f"cat:{c}" for c in categories)
        search_query = f"({cat_query})"
    else:
        search_query = "all:*"

    url = (
        f"{BASE_URL}?search_query={urllib.parse.quote(search_query, safe='+()')}"
        f"&start=0&max_results={max_results}"
        "&sortBy=submittedDate&sortOrder=descending"
    )
    feed = feedparser.parse(url)

    papers = []
    for entry in feed.entries:
        published = entry.get("published", "")[:10]
        papers.append({
            "id": entry.get("id", entry.link),
            "title": " ".join(entry.title.split()),
            "summary": " ".join(entry.summary.split()),
            "authors": [a.name for a in entry.get("authors", [])],
            "link": entry.link,
            "published": published,
            "source": "arxiv",
        })
    return papers
