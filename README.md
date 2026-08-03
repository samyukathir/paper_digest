# Paper Digest Agent

Finds new papers relevant to your research interests and writes a digest
into this repo — no email required. Pipeline:

```
fetch (7 sources) -> dedupe -> drop already-seen -> embedding pre-filter
  (free, local) -> Claude relevance judgment + write-up -> digests/YYYY-MM-DD.md
```

## Sources

| Source | Coverage | Key required? |
|---|---|---|
| arXiv | CS/ML/physics/math/q-bio preprints | No |
| PubMed | Biomedical literature | No |
| bioRxiv / medRxiv | Biology & medical preprints | No |
| Semantic Scholar | Cross-discipline | No (optional, raises rate limit) |
| Europe PMC | Biomedical literature + preprints | No |
| OpenAlex | Very broad, nearly all published works | No (optional email for polite pool) |
| Nature (Springer) | Nature-family journals | **Yes** — disabled by default |
| ScienceDirect (Elsevier) | Elsevier journals | **Yes** — disabled by default, metadata-only without institutional access |

**Google Scholar is intentionally not included.** It has no public API;
scraping it violates Google's Terms of Service and gets blocked by
captchas quickly. If you want Scholar-quality coverage, Semantic Scholar
and OpenAlex already index most of what Scholar shows. If you still want
it, you can wire up a paid third-party proxy like [SerpApi](https://serpapi.com)
yourself — a `SERPAPI_API_KEY` slot is left in `.env.example` for that.

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   First run downloads a small (~80MB) local embedding model — one-time,
   no API cost.

2. **Configure secrets**
   ```bash
   cp .env.example .env
   ```
   Fill in:
   - `ANTHROPIC_API_KEY` — required, from https://console.anthropic.com
   - Everything else in `.env.example` is optional and only needed if you
     enable the corresponding source, or switch delivery to email (see
     "Alternative: email delivery" below).

3. **Edit `config.yaml`** (no personal info goes here — it's safe to commit)
   - `interest_description` — already pre-filled for AI/ML, healthcare/EHR,
     computational pathology, genomics, and bioinformatics. Edit freely.
   - `sources.*.enabled` — toggle sources on/off.
   - `delivery.file.output_dir` — folder digests are written to (default
     `digests/`).

4. **Run it**
   ```bash
   python main.py
   ```
   Writes a new file to `digests/<today's date>.md` with the relevant
   papers, ranked by importance, each with a title/link, summary, and a
   one-line "why it matters." On first run, everything fetched counts as
   "new" — expect a larger digest. Subsequent runs only surface genuinely
   new papers (tracked in `.state/seen_papers.json`).

## API usage

If you want to run the digest through an HTTP API instead of a CLI:

1. Install the API dependencies:
   ```bash
   pip install fastapi uvicorn pydantic
   ```
2. Start the server from the repo root:
   ```bash
   uvicorn api:app --reload --host 127.0.0.1 --port 8000
   ```
3. Post a digest request:
   ```bash
   curl -X POST http://127.0.0.1:8000/digest \
     -H "Content-Type: application/json" \
     -d '{"config_path": "config.yaml", "write_output": true, "mark_seen": true}'
   ```

The API returns the digest items plus metadata about fetched, unseen, and
pre-filtered paper counts.

## Automating it (GitHub Actions)

A workflow is included at `.github/workflows/digest.yml`, scheduled daily
at 13:00 UTC (edit the `cron:` line for your preferred time). Each run
writes a new file to `digests/` and commits it back to the repo — so the
repo itself becomes your archive of every digest, browsable on GitHub.

1. Push this project to a GitHub repo (public or private — no personal
   info is written to any tracked file).
2. In repo Settings → Secrets and variables → Actions, add:
   - `ANTHROPIC_API_KEY` (required)
   - `SEMANTIC_SCHOLAR_API_KEY`, `OPENALEX_MAILTO`, `SPRINGER_NATURE_API_KEY`,
     `ELSEVIER_API_KEY` (optional, only if you use those sources)
3. That's it — it runs on schedule, and you can trigger it manually from
   the Actions tab (`workflow_dispatch`). The workflow needs `contents:
   write` permission to commit digests back, which is already set in the
   workflow file.

**State persistence:** `.state/seen_papers.json` (the "already notified"
tracker) is committed back to the repo after every run, alongside the
digest file — so it survives reliably across runs, unlike a GitHub Actions
cache (which can be evicted after 7 days unused). The `lookback_days`
setting (default 2) also gives a small overlap window as a safety net.

## Alternative: email delivery

The original email-based delivery is still built in (`emailer.py`), just
not the default. To use it:

1. Set `delivery.method: "email"` in `config.yaml`.
2. Fill in `SMTP_USER`, `SMTP_PASS`, `EMAIL_TO`, `EMAIL_FROM` in `.env` (or
   as GitHub Secrets, and uncomment those lines in the workflow's `env:`
   block). Works with any SMTP provider, not just Gmail — set
   `delivery.email.smtp_host` / `smtp_port` to match yours (e.g.
   `smtp.office365.com:587`, `smtp.mail.yahoo.com:465`). Note: the current
   `emailer.py` only implements SSL (port 465) connections; STARTTLS
   providers (port 587, e.g. Outlook/iCloud) would need a small tweak to
   `smtplib.SMTP` + `.starttls()` instead of `SMTP_SSL`.

## Cost

- Embedding pre-filter: **free**, runs locally.
- Claude pass: only the pre-filtered shortlist (≤ `max_candidates_for_llm`,
  default 30) goes to the model, using Haiku. Typically a few cents/month
  at daily-run cadence.

## Tuning

- `min_relevance_score` (config.yaml) — raise to reduce noise, lower to
  catch more borderline-relevant papers.
- `lookback_days` — how far back each run searches. Keep ≥ your run
  frequency so nothing falls in a gap.
- `max_digest_items` — cap on papers per digest file.

## Extending

- **Add a source:** create `fetchers/yourname.py` with a
  `fetch(cfg, lookback_days) -> list[dict]` function returning dicts with
  keys `id, title, summary, authors, link, published, source`. Register it
  in `FETCHERS` in `main.py` and add a `sources.yourname` block to
  `config.yaml`.
- **Swap delivery for Slack/Discord:** add a new module alongside
  `file_writer.py`/`emailer.py`, branch on it in `main.py`'s delivery
  section; the `digest_items` list already has everything you need
  (title, link, summary, why_relevant, importance).
