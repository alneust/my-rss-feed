import re
from bs4 import BeautifulSoup
import feedparser
from feedgen.feed import FeedGenerator

SOURCE_FEED = "https://www.nationalreview.com/author/wesley-j-smith/feed/"
OUTPUT_FILE = "feed.xml"
MAX_ITEMS = 10


def build_full_rss():
    parsed = feedparser.parse(SOURCE_FEED)

    fg = FeedGenerator()
    fg.load_extension("media")
    fg.id("https://www.nationalreview.com/author/wesley-j-smith/")
    fg.title("Wesley J. Smith - National Review (Archive Feed)")
    fg.link(
        href="https://www.nationalreview.com/author/wesley-j-smith/",
        rel="alternate",
    )
    fg.description("Paywall-free RSS feed generated via GitHub Actions.")

    for entry in parsed.entries[:MAX_ITEMS]:
        original_url = entry.get("link", "")
        title = entry.get("title", "Untitled")

        # Route links through Archive.today to bypass paywalls reliably
        clean_url = (
            f"https://archive.today/newest/{original_url}"
            if original_url
            else ""
        )

        fe = fg.add_entry()
        fe.id(entry.get("id", original_url))
        fe.title(title)
        fe.link(href=clean_url)

        if "published" in entry:
            fe.published(entry.published)

        # 1. Extract content/summary
        raw_summary = entry.get("summary", entry.get("description", ""))

        # 2. Extract image URL from feed enclosures or media tags
        image_url = None
        if "media_content" in entry and len(entry.media_content) > 0:
            image_url = entry.media_content[0].get("url")
        elif "media_thumbnail" in entry and len(entry.media_thumbnail) > 0:
            image_url = entry.media_thumbnail[0].get("url")

        if not image_url and "enclosures" in entry and len(entry.enclosures) > 0:
            image_url = entry.enclosures[0].get("href")

        if not image_url and raw_summary:
            soup_img = BeautifulSoup(raw_summary, "html.parser")
            img_tag = soup_img.find("img")
            if img_tag and img_tag.get("src"):
                image_url = img_tag["src"]

        # 3. Clean summary text snippet for description
        soup_desc = BeautifulSoup(raw_summary, "html.parser")
        clean_text = soup_desc.get_text().strip()
        clean_text = re.sub(
            r"Become a member.*", "", clean_text, flags=re.IGNORECASE
        )
        fe.description(
            clean_text if clean_text else "Click to read full article."
        )

        # 4. Construct clean HTML content with lead thumbnail
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
