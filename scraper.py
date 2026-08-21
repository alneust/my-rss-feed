import re
from bs4 import BeautifulSoup
import feedparser
from feedgen.feed import FeedGenerator

SOURCE_FEED = "https://www.nationalreview.com/author/wesley-j-smith/feed/"
OUTPUT_FILE = "feed.xml"
MAX_ITEMS = 10


def build_full_rss():
    # Parse National Review's official author RSS feed
    parsed = feedparser.parse(SOURCE_FEED)

    fg = FeedGenerator()
    # Enable Media RSS extension for WordPress thumbnail support
    fg.load_extension("media")
    fg.id("https://www.nationalreview.com/author/wesley-j-smith/")
    fg.title("Wesley J. Smith - National Review")
    fg.link(
        href="https://www.nationalreview.com/author/wesley-j-smith/",
        rel="alternate",
    )
    fg.description("Clean RSS feed generated for WordPress.")

    for entry in parsed.entries[:MAX_ITEMS]:
        url = entry.get("link", "")
        title = entry.get("title", "Untitled")

        fe = fg.add_entry()
        fe.id(entry.get("id", url))
        fe.title(title)
        fe.link(href=url)

        if "published" in entry:
            fe.published(entry.published)

        # 1. Extract raw content/summary provided inside the feed
        raw_summary = entry.get("summary", entry.get("description", ""))

        # 2. Extract image URL from feed enclosures or media tags
        image_url = None

        # Check media content / media thumbnail tags
        if "media_content" in entry and len(entry.media_content) > 0:
            image_url = entry.media_content[0].get("url")
        elif "media_thumbnail" in entry and len(entry.media_thumbnail) > 0:
            image_url = entry.media_thumbnail[0].get("url")

        # Check standard enclosures
        if not image_url and "enclosures" in entry and len(entry.enclosures) > 0:
            image_url = entry.enclosures[0].get("href")

        # Fallback: check inline <img> tags in the summary
        if not image_url and raw_summary:
            soup_img = BeautifulSoup(raw_summary, "html.parser")
            img_tag = soup_img.find("img")
            if img_tag and img_tag.get("src"):
                image_url = img_tag["src"]

        # 3. Clean up description for WordPress snippet
        soup_desc = BeautifulSoup(raw_summary, "html.parser")
        clean_text = soup_desc.get_text().strip()

        # Remove paywall and popup references from plain text
        clean_text = re.sub(
            r"Become a member.*", "", clean_text, flags=re.IGNORECASE
        )
        fe.description(
            clean_text if clean_text else "Click to read full article."
        )

        # 4. Construct clean HTML content with thumbnail image
        content_html = ""
        if image_url:
            # Set enclosure & Media RSS thumbnail tag for WordPress
            fe.enclosure(url=image_url, type="image/jpeg", length="0")
            fe.media.thumbnail(url=image_url)

            # Prepend lead image directly into feed content
            content_html += f'<p><img src="{image_url}" style="max-width:100%; height:auto;" /></p>'

        content_html += f"<div>{raw_summary}</div>"
        fe.content(content_html, type="CDATA")

    fg.rss_file(OUTPUT_FILE, pretty=True)


if __name__ == "__main__":
    build_full_rss()
