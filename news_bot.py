"""
Sends new news items to Telegram, grouped by topic.
Tracks what's already been sent using seen.json (committed back to the repo by the GitHub Action).
"""

import feedparser
import requests
import json
import os
import re
import html

TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
SEEN_FILE = "seen.json"
MAX_PER_FEED_ON_FIRST_RUN = 3  # avoid flooding you on the very first run

# Feeds grouped by topic. Add/remove URLs anytime.
FEEDS = {
    "Tech": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
    ],
    "Finance": [
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",  # CNBC Finance
        "https://www.moneycontrol.com/rss/latestnews.xml",
    ],
    "India": [
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
    ],
    "World / Geopolitics": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "Oil / Gas / Commodities": [
        "https://oilprice.com/rss/main",
    ],
    "Markets": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
    ],
}


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen)[-3000:], f)  # keep file bounded


def clean(text, limit=280):
    text = re.sub(r"<[^>]+>", "", text or "")
    text = html.unescape(text).strip()
    return text[:limit]


def send_telegram(text):
    resp = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=15,
    )
    if not resp.ok:
        print("Telegram error:", resp.status_code, resp.text)


def main():
    seen = load_seen()
    is_first_run = len(seen) == 0
    new_seen = set(seen)

    for topic, urls in FEEDS.items():
        for url in urls:
            try:
                parsed = feedparser.parse(url)
            except Exception as e:
                print(f"Failed to parse {url}: {e}")
                continue

            entries = parsed.entries
            if is_first_run:
                entries = entries[:MAX_PER_FEED_ON_FIRST_RUN]

            for entry in entries:
                uid = entry.get("id") or entry.get("link")
                if not uid or uid in seen:
                    continue

                title = clean(entry.get("title", "(no title)"), 200)
                summary = clean(entry.get("summary", entry.get("description", "")), 280)
                link = entry.get("link", "")

                message = f"<b>[{topic}] {html.escape(title)}</b>\n{html.escape(summary)}"
                if link:
                    message += f"\n{link}"

                send_telegram(message)
                new_seen.add(uid)

    save_seen(new_seen)


if __name__ == "__main__":
    main()
