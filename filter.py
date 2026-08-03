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


def rank_papers(papers, interest_description, min_score=0.30, top_k=30):
    if not papers:
        return []

    model = _get_model()
    interest_emb = model.encode(interest_description, convert_to_tensor=True)

    texts = [f"{p['title']}. {p.get('summary', '')}".strip() for p in papers]
    embs = model.encode(texts, convert_to_tensor=True, show_progress_bar=False)
    scores = util.cos_sim(interest_emb, embs)[0].tolist()

    for p, score in zip(papers, scores):
        p["score"] = round(score, 4)

    ranked = sorted(papers, key=lambda p: p["score"], reverse=True)
    filtered = [p for p in ranked if p["score"] >= min_score]
    return filtered[:top_k]
