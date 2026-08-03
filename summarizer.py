"""Final relevance judgment + digest write-up, via Claude."""
import json

import anthropic

client = anthropic.Anthropic()

_SYSTEM_PROMPT = """You are filtering and summarizing academic papers for a \
researcher's personal digest. You will be given the researcher's interests \
and a list of candidate papers. For each paper that is genuinely relevant, \
produce a short digest entry. Skip papers that only superficially match \
keywords but aren't actually relevant.

Respond with ONLY a JSON array (no prose, no markdown fences) where each \
element has exactly these keys:
  "index": the paper's index number as given in the input
  "summary": a 1-2 sentence plain-language summary of the paper
  "why_relevant": a 1 sentence explanation of why it matters to this \
researcher specifically
  "importance": one of "high", "medium", "low"

Order the array by importance (high first). Omit irrelevant papers entirely."""


def _build_user_prompt(papers, interest_description):
    lines = [f"My research interests: {interest_description}\n", "Candidate papers:\n"]
    for i, p in enumerate(papers):
        summary = p.get("summary") or "(no abstract available)"
        lines.append(
            f"[{i}] Title: {p['title']}\n"
            f"Source: {p.get('source', '')}\n"
            f"Abstract: {summary}\n"
        )
    return "\n".join(lines)


def build_digest(papers, interest_description, model, max_tokens):
    if not papers:
        return []

    prompt = _build_user_prompt(papers, interest_description)
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = message.content[0].text.strip()

    try:
        judgments = json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("[")
        end = raw_text.rfind("]")
        if start == -1 or end == -1:
            return []
        try:
            judgments = json.loads(raw_text[start:end + 1])
        except json.JSONDecodeError:
            return []

    digest_items = []
    for j in judgments:
        idx = j.get("index")
        if idx is None or not (0 <= idx < len(papers)):
            continue
        paper = papers[idx]
        digest_items.append({
            "title": paper["title"],
            "link": paper["link"],
            "source": paper.get("source", ""),
            "published": paper.get("published", ""),
            "summary": j.get("summary", ""),
            "why_relevant": j.get("why_relevant", ""),
            "importance": j.get("importance", "medium"),
        })
    return digest_items
