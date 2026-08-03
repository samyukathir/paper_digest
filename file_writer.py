"""Writes the digest to a markdown file in the repo instead of emailing it."""
import os
from datetime import date

_IMPORTANCE_ORDER = {"high": 0, "medium": 1, "low": 2}
_IMPORTANCE_LABEL = {"high": "High", "medium": "Medium", "low": "Low"}


def _render_markdown(digest_items, interest_description, run_date):
    lines = [
        f"# Paper Digest — {run_date}",
        "",
        f"_Interests: {interest_description.strip()}_",
        "",
    ]

    if not digest_items:
        lines.append("No new relevant papers found today.")
        return "\n".join(lines) + "\n"

    items_sorted = sorted(digest_items, key=lambda d: _IMPORTANCE_ORDER.get(d["importance"], 1))

    for item in items_sorted:
        label = _IMPORTANCE_LABEL.get(item["importance"], "Medium")
        lines.append(f"## [{item['title']}]({item['link']})")
        lines.append(f"**{label}** · {item.get('source', '')} · {item.get('published', '')}")
        lines.append("")
        lines.append(item["summary"])
        lines.append("")
        lines.append(f"*Why it matters: {item['why_relevant']}*")
        lines.append("")

    return "\n".join(lines) + "\n"


def write_digest(digest_items, interest_description, file_cfg, base_dir=None):
    output_dir = file_cfg.get("output_dir", "digests")
    if base_dir:
        output_dir = os.path.join(base_dir, output_dir)
    os.makedirs(output_dir, exist_ok=True)

    run_date = date.today().isoformat()
    out_path = os.path.join(output_dir, f"{run_date}.md")

    markdown = _render_markdown(digest_items, interest_description, run_date)
    with open(out_path, "w") as f:
        f.write(markdown)

    return out_path
