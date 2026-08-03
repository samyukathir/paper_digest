"""Email delivery via SMTP (e.g. Gmail with an App Password)."""
import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

_IMPORTANCE_ORDER = {"high": 0, "medium": 1, "low": 2}


def _render_html(digest_items, interest_description):
    if not digest_items:
        return "<p>No new relevant papers found today.</p>"

    items_sorted = sorted(digest_items, key=lambda d: _IMPORTANCE_ORDER.get(d["importance"], 1))

    rows = []
    for item in items_sorted:
        badge_color = {"high": "#c0392b", "medium": "#e67e22", "low": "#7f8c8d"}.get(item["importance"], "#7f8c8d")
        rows.append(f"""
        <div style="margin-bottom:20px;padding:14px;border:1px solid #e0e0e0;border-radius:8px;">
          <div style="font-size:11px;color:{badge_color};font-weight:bold;text-transform:uppercase;">
            {item['importance']} &middot; {item.get('source', '')} &middot; {item.get('published', '')}
          </div>
          <a href="{item['link']}" style="font-size:16px;font-weight:bold;color:#1a5276;text-decoration:none;">
            {item['title']}
          </a>
          <p style="margin:8px 0 4px 0;color:#333;">{item['summary']}</p>
          <p style="margin:0;color:#555;font-style:italic;">Why it matters: {item['why_relevant']}</p>
        </div>
        """)

    return f"""
    <html><body style="font-family:sans-serif;max-width:700px;margin:auto;">
      <h2>Paper Digest — {date.today().isoformat()}</h2>
      <p style="color:#666;font-size:13px;">Interests: {interest_description}</p>
      {''.join(rows)}
    </body></html>
    """


def send_digest(digest_items, interest_description, delivery_cfg):
    email_cfg = delivery_cfg["email"]
    user = os.environ.get(email_cfg["user_env"], "")
    password = os.environ.get(email_cfg["pass_env"], "")
    to_addr = os.environ.get(email_cfg["to_env"], "")
    from_addr = os.environ.get(email_cfg["from_env"], "")
    missing = [
        name for name, val in [
            (email_cfg["user_env"], user),
            (email_cfg["pass_env"], password),
            (email_cfg["to_env"], to_addr),
            (email_cfg["from_env"], from_addr),
        ] if not val
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)} "
            "(set them in your .env or as GitHub Actions secrets)"
        )

    html = _render_html(digest_items, interest_description)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Paper Digest — {date.today().isoformat()} ({len(digest_items)} papers)"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL(email_cfg["smtp_host"], email_cfg["smtp_port"]) as server:
        server.login(user, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())
