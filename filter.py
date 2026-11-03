"""Embedding-based relevance pre-filter. Local model, no API cost."""
from sentence_transformers import SentenceTransformer, util

_MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def dedupe(papers):
    seen = set()
    deduped = []
    for p in papers:
        key = p.get("id") or p["title"].strip().lower()
        title_key = p["title"].strip().lower()
        if key in seen or title_key in seen:
            continue
        seen.add(key)
        seen.add(title_key)
        deduped.append(p)
    return deduped


def rank_papers(papers, interest_description, min_score=0.30, top_k=30, interest_topics=None):
    """Score papers against your interests and keep the best ones.

    If `interest_topics` (a list of short descriptions) is given, each paper
    is compared to every topic and scored by its BEST match, so a paper that
    fits just one topic isn't penalised for not covering the others.
    Otherwise falls back to comparing against the single
    `interest_description` paragraph (the original behaviour).
    """
    if not papers:
        return []

    topics = [t.strip() for t in (interest_topics or []) if t and t.strip()]
    if not topics:
        topics = [interest_description]

    model = _get_model()
    topic_embs = model.encode(topics, convert_to_tensor=True, show_progress_bar=False)

    texts = [f"{p['title']}. {p.get('summary', '')}".strip() for p in papers]
    paper_embs = model.encode(texts, convert_to_tensor=True, show_progress_bar=False)

    # sims has shape (num_topics, num_papers); take the best topic per paper
    sims = util.cos_sim(topic_embs, paper_embs)
    best_scores, best_topic_idx = sims.max(dim=0)

    for p, score, t_idx in zip(papers, best_scores.tolist(), best_topic_idx.tolist()):
        p["score"] = round(score, 4)
        p["matched_topic"] = topics[t_idx]

    ranked = sorted(papers, key=lambda p: p["score"], reverse=True)
    filtered = [p for p in ranked if p["score"] >= min_score]
    return filtered[:top_k]
