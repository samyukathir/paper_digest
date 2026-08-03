#!/usr/bin/env python3
"""Paper Digest Agent — orchestrator.

Pipeline: fetch from enabled sources -> dedupe -> drop already-seen papers
-> embedding pre-filter -> Claude relevance judgment + digest write-up
-> delivery (file or email) -> record seen papers.
"""
import os
import sys

import yaml

import filter as relevance_filter
import state
from file_writer import write_digest
from fetchers import (
    arxiv,
    biorxiv_medrxiv,
    europe_pmc,
    nature,
    openalex,
    pubmed,
    sciencedirect,
    semantic_scholar,
)
from summarizer import build_digest

FETCHERS = {
    "arxiv": arxiv,
    "pubmed": pubmed,
    "biorxiv_medrxiv": biorxiv_medrxiv,
    "semantic_scholar": semantic_scholar,
    "europe_pmc": europe_pmc,
    "openalex": openalex,
    "nature": nature,
    "sciencedirect": sciencedirect,
}


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def fetch_all(config):
    lookback_days = config.get("lookback_days", 2)
    all_papers = []
    for name, module in FETCHERS.items():
        src_cfg = config["sources"].get(name, {})
        if not src_cfg.get("enabled"):
            continue
        print(f"Fetching from {name}...", file=sys.stderr)
        try:
            papers = module.fetch(src_cfg, lookback_days)
        except Exception as e:
            print(f"  {name} fetch failed: {e}", file=sys.stderr)
            continue
        print(f"  got {len(papers)} papers", file=sys.stderr)
        all_papers.extend(papers)
    return all_papers


def main():
    config = load_config()

    papers = fetch_all(config)
    papers = relevance_filter.dedupe(papers)
    print(f"Total unique papers fetched: {len(papers)}", file=sys.stderr)

    seen_ids = state.load_seen_ids()
    papers = state.filter_unseen(papers, seen_ids)
    print(f"New (unseen) papers: {len(papers)}", file=sys.stderr)

    candidates = relevance_filter.rank_papers(
        papers,
        config["interest_description"],
        min_score=config.get("min_relevance_score", 0.30),
        top_k=config.get("max_candidates_for_llm", 30),
    )
    print(f"Pre-filtered candidates for LLM pass: {len(candidates)}", file=sys.stderr)

    digest_items = build_digest(
        candidates,
        config["interest_description"],
        model=config["llm"]["model"],
        max_tokens=config["llm"]["max_tokens"],
    )
    digest_items = digest_items[: config.get("max_digest_items", 15)]
    print(f"Final digest items: {len(digest_items)}", file=sys.stderr)

    method = config["delivery"]["method"]
    if method == "file":
        base_dir = os.path.dirname(os.path.abspath(__file__))
        out_path = write_digest(
            digest_items, config["interest_description"], config["delivery"]["file"], base_dir=base_dir
        )
        print(f"Digest written to {out_path}", file=sys.stderr)
    elif method == "email":
        from emailer import send_digest
        send_digest(digest_items, config["interest_description"], config["delivery"])
        print("Digest emailed.", file=sys.stderr)
    else:
        print(f"Unknown delivery method: {method}", file=sys.stderr)

    all_fetched_ids = {p["id"] for p in papers if p.get("id")}
    seen_ids.update(all_fetched_ids)
    state.save_seen_ids(seen_ids)


def build_digest_items(config):
    papers = fetch_all(config)
    papers = relevance_filter.dedupe(papers)
    total_unique_papers = len(papers)

    seen_ids = state.load_seen_ids()
    papers = state.filter_unseen(papers, seen_ids)
    new_papers = len(papers)

    candidates = relevance_filter.rank_papers(
        papers,
        config["interest_description"],
        min_score=config.get("min_relevance_score", 0.30),
        top_k=config.get("max_candidates_for_llm", 30),
    )

    digest_items = build_digest(
        candidates,
        config["interest_description"],
        model=config["llm"]["model"],
        max_tokens=config["llm"]["max_tokens"],
    )
    digest_items = digest_items[: config.get("max_digest_items", 15)]

    all_fetched_ids = {p["id"] for p in papers if p.get("id")}
    return {
        "digest_items": digest_items,
        "total_unique_papers": total_unique_papers,
        "new_papers": new_papers,
        "pre_filtered_candidates": len(candidates),
        "all_fetched_ids": all_fetched_ids,
    }


if __name__ == "__main__":
    main()
