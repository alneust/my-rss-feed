import re
from bs4 import BeautifulSoup
import feedparser
from feedgen.feed import FeedGenerator
import requests

# Direct author feed
SOURCE_FEED = "https://www.nationalreview.com/author/wesley-j-smith/feed/"
OUTPUT_FILE = "feed.xml"
MAX_ITEMS = 10


def build_full_rss():
    parsed = feedparser.parse(SOURCE_FEED)

    fg = FeedGenerator()
    fg.load_extension("media")
    fg.id("https://www.nationalreview.com/author/wesley-j-smith/")
    fg.title("Wesley J. Smith - National Review")
    fg.link(
        href="https://www.nationalreview.com/author/wesley-j-smith/",
        rel="alternate",
    )
    fg.description("Clean RSS feed generated for WordPress.")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    for entry in parsed.entries[:MAX_ITEMS]:
        url = entry.get("link", "")
        title = entry.get("title", "Untitled")

        fe = fg.add_entry()
        fe.id(entry.get("id", url))
        fe.title(title)
        fe.link(href=url)

        if "published" in entry:
            fe.published(entry.published)

        # 1. Extract content and description from source
        raw_summary = entry.get("summary", entry.get("description", ""))

        # 2. Extract lead thumbnail image
        image_url = None
        if "enclosures" in entry and len(entry.enclosures) > 0:
            image_url = entry.enclosures[0].get("href")

        if not image_url and url:
            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    og_img = soup.find("meta", property="og:image")
                    if og_img and og_img.get("content"):
                        image_url = og_img["content"]
            except Exception as e:
                print(f"Error fetching image for {url}: {e}")

        # 3. Clean text snippet
        soup_desc = BeautifulSoup(raw_summary, "html.parser")
        clean_text = soup_desc.get_text()
        fe.description(
            clean_text if clean_text else "Click to read full article."
        )

        # 4. Format clean HTML content and thumbnails
        content_html = ""
        if image_url:
            fe.enclosure(url=image_url, type="image/jpeg", length="0")
            fe.media.thumbnail(url=image_url)
            content_html += f'<p><img src="{image_url}" style="max-width:100%; height:auto;" /></p>'

        content_html += f"<div>{raw_summary}</div>"
        fe.content(content_html, type="CDATA")

    fg.rss_file(OUTPUT_FILE, pretty=True)


if __name__ == "__main__":
    build_full_rss()
