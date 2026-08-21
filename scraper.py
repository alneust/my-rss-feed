import re
from bs4 import BeautifulSoup
import feedparser
from feedgen.feed import FeedGenerator
from playwright.sync_api import sync_playwright
from readability import Document

SOURCE_FEED = "https://www.nationalreview.com/author/wesley-j-smith/feed/"
OUTPUT_FILE = "feed.xml"
MAX_ITEMS = 5  # Keep low so GitHub Actions doesn't time out rendering pages


def fetch_full_article_content(page, url):
    """Launches headless Chrome to render JavaScript and extract full text like Morss.it."""
    try:
        # Navigate to page and wait until DOM content loads
        page.goto(url, wait_until="domcontentloaded", timeout=15000)

        # Get fully rendered HTML source
        html_content = page.content()

        # Parse main article body using Readability (same engine Firefox/Morss uses)
        doc = Document(html_content)
        clean_html = doc.summary()

        return clean_html
    except Exception as e:
        print(f"Failed to extract full text for {url}: {e}")
        return ""


def build_full_rss():
    parsed = feedparser.parse(SOURCE_FEED)

    fg = FeedGenerator()
    fg.load_extension("media")
    fg.id("https://www.nationalreview.com/author/wesley-j-smith/")
    fg.title("Wesley J. Smith - National Review (Full Content Feed)")
    fg.link(
        href="https://www.nationalreview.com/author/wesley-j-smith/",
        rel="alternate",
    )
    fg.description("Full-text unpaywalled feed generated via Headless Chrome.")

    # Start Playwright Headless Browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use a real desktop browser user-agent to pass bot checks
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for entry in parsed.entries[:MAX_ITEMS]:
            url = entry.get("link", "")
            title = entry.get("title", "Untitled")

            fe = fg.add_entry()
            fe.id(entry.get("id", url))
            fe.title(title)
            fe.link(href=url)

            if "published" in entry:
                fe.published(entry.published)

            # 1. Fetch full article HTML body using Playwright browser
            print(f"Scraping full text: {url}")
            full_body_html = fetch_full_article_content(page, url)

            # Fallback to feed summary if Playwright extraction fails
            raw_summary = entry.get("summary", entry.get("description", ""))
            if not full_body_html:
                full_body_html = raw_summary

            # 2. Extract Lead Image
            image_url = None
            if "media_content" in entry and len(entry.media_content) > 0:
                image_url = entry.media_content[0].get("url")

            if not image_url and raw_summary:
                soup_img = BeautifulSoup(raw_summary, "html.parser")
                img_tag = soup_img.find("img")
                if img_tag and img_tag.get("src"):
                    image_url = img_tag["src"]

            # 3. Create clean text summary for ticker preview
            soup_desc = BeautifulSoup(full_body_html, "html.parser")
            clean_text = soup_desc.get_text().strip()[:300] + "..."
            fe.description(clean_text)

            # 4. Format full content payload + enclosure images
            content_html = ""
            if image_url:
                fe.enclosure(url=image_url, type="image/jpeg", length="0")
                fe.media.thumbnail(url=image_url)
                content_html += f'<p><img src="{image_url}" style="max-width:100%; height:auto;" /></p>'

            content_html += f"<div>{full_body_html}</div>"
            fe.content(content_html, type="CDATA")

        browser.close()

    fg.rss_file(OUTPUT_FILE, pretty=True)


if __name__ == "__main__":
    build_full_rss()
