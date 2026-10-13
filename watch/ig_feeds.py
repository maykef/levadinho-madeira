#!/usr/bin/env python3
"""RSS for the watch's official Instagram accounts, from our own phone capture (2026-10-11).

Instagram refuses logged-out profile reads since 2026-10-08 (401 "require_login"), so RSSHub's /instagram/user/<handle>
answers 503 "Please set INSTAGRAM_COOKIE" for every account. The phone's logged-in Instagram app now visits these
profiles (socialwatch/android/instagram_agent.py, surface official:a|b|c) and stores their newest posts in
levadinho-db social.post; this job writes them as RSS 2.0, one file per handle:

    watch/state/feeds/instagram_<handle>.xml   (lw-apply reads file:///app/state/feeds/…, storm_watch.py the host path)

An account with nothing captured yet gets a valid empty feed (no error). Collect job `ig_feeds`, every 10 min.
"""
import json, os, sys
from datetime import timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
SW = os.path.join(HERE, "..", "seo_research", "funchal", "socialwatch")
sys.path.insert(0, os.path.join(SW, "db"))
import psycopg                                            # noqa: E402
from swdb import db_url                                   # noqa: E402

OUT = os.path.join(HERE, "state", "feeds")
ITEMS = 20


def handles():
    """The ig_* sources in sources.json → their handles (file:// or RSSHub form)."""
    src = json.load(open(os.path.join(HERE, "sources.json")))["sources"]
    out = []
    for s in src:
        u = s.get("url", "")
        if "/instagram/user/" in u:
            out.append(u.rsplit("/", 1)[1])
        elif "/feeds/instagram_" in u:
            out.append(u.rsplit("instagram_", 1)[1].removesuffix(".xml"))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    conn = psycopg.connect(db_url())
    summary = []
    for h in handles():
        rows = conn.execute("""select url, caption, posted_at from social.post
                               where platform = 'instagram' and url is not null
                                 -- joint posts are stored as "madeira_gov   and juventudemadeira"
                                 and lower(author) ~ ('^' || lower(%s) || '( |$)')
                               order by posted_at desc nulls last limit %s""", (h, ITEMS)).fetchall()
        items = []
        for url, cap, posted in rows:
            cap = (cap or "").strip()
            title = (cap.splitlines()[0] if cap else "Instagram post")[:120]
            items.append(f"<item><title>{escape(title)}</title><link>{escape(url)}</link><guid isPermaLink=\"true\">{escape(url)}</guid>"
                         + (f"<pubDate>{format_datetime(posted.astimezone(timezone.utc), usegmt=True)}</pubDate>" if posted else "")
                         + f"<description>{escape(cap)}</description></item>")
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
               f"<title>{escape(h)} (Instagram, Levadinho phone capture)</title><link>https://www.instagram.com/{escape(h)}/</link>"
               "<description>Newest posts read by the Levadinho phone</description>" + "".join(items) + "</channel></rss>\n")
        path = os.path.join(OUT, f"instagram_{h}.xml")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(xml)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
        summary.append(f"{h}={len(items)}")
    print("feeds: " + " ".join(summary))


if __name__ == "__main__":
    main()
