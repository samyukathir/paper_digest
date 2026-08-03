"""PubMed fetcher via NCBI E-utilities. Free, no key required (but a
low rate limit applies — this module deliberately makes few requests)."""
import xml.etree.ElementTree as ET

import requests

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _search_ids(term, reldate, retmax):
    params = {
        "db": "pubmed",
        "term": term,
        "retmax": retmax,
        "datetype": "pdat",
        "reldate": reldate,
        "sort": "date",
        "retmode": "json",
    }
    resp = requests.get(ESEARCH_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("esearchresult", {}).get("idlist", [])


def _fetch_details(pmids):
    if not pmids:
        return []
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
    }
    resp = requests.get(EFETCH_URL, params=params, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    papers = []
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        pmid = pmid_el.text if pmid_el is not None else None

        title_el = article.find(".//ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""

        abstract_parts = article.findall(".//Abstract/AbstractText")
        summary = " ".join("".join(p.itertext()).strip() for p in abstract_parts)

        authors = []
        for author in article.findall(".//AuthorList/Author"):
            last = author.find("LastName")
            fore = author.find("ForeName")
            if last is not None and fore is not None:
                authors.append(f"{fore.text} {last.text}")

        pubdate_el = article.find(".//ArticleDate") or article.find(".//PubDate")
        published = ""
        if pubdate_el is not None:
            year = pubdate_el.findtext("Year", "")
            month = pubdate_el.findtext("Month", "01").zfill(2) if pubdate_el.findtext("Month", "").isdigit() else "01"
            day = pubdate_el.findtext("Day", "01").zfill(2)
            published = f"{year}-{month}-{day}" if year else ""

        if not title or not pmid:
            continue

        papers.append({
            "id": f"pubmed:{pmid}",
            "title": title,
            "summary": summary,
            "authors": authors,
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "published": published,
            "source": "pubmed",
        })
    return papers


def fetch(cfg, lookback_days):
    search_terms = cfg.get("search_terms", [])
    max_results = cfg.get("max_results", 60)
    per_term = max(1, max_results // max(1, len(search_terms)))

    seen_ids = set()
    papers = []
    for term in search_terms:
        try:
            ids = _search_ids(term, lookback_days, per_term)
        except requests.RequestException:
            continue
        new_ids = [i for i in ids if i not in seen_ids]
        seen_ids.update(new_ids)
        try:
            papers.extend(_fetch_details(new_ids))
        except requests.RequestException:
            continue
    return papers
