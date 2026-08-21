import re
from bs4 import BeautifulSoup
import feedparser
from feedgen.feed import FeedGenerator
from playwright.sync_api import sync_playwright
from readability import Document

SOURCE_FEED = "https://www.nationalreview.com/author/wesley-j-smith/feed/"
OUTPUT_FILE = "feed.xml"
MAX_ITEMS = 5


def fetch_full_article_content(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        html_content = page.content()
        doc = Document(html_content)
        return doc.summary()
    except Exception as e:
        print(f"Skipping full text for {url}: {e}")
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
    fg.description("Full-text feed generated via Headless Chrome.")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
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

                full_body_html = fetch_full_article_content(page, url)
                raw_summary = entry.get("summary", entry.get("description", ""))
                if not full_body_html:
                    full_body_html = raw_summary

                image_url = None
                if "media_content" in entry and len(entry.media_content) > 0:
                    image_url = entry.media_content[0].get("url")

                if not image_url and raw_summary:
                    soup_img = BeautifulSoup(raw_summary, "html.parser")
                    img_tag = soup_img.find("img")
                    if img_tag and img_tag.get("src"):
                        image_url = img_tag["src"]

                soup_desc = BeautifulSoup(full_body_html, "html.parser")
                clean_text = soup_desc.get_text().strip()[:300] + "..."
                fe.description(clean_text)

                content_html = ""
                if image_url:
                    fe.enclosure(url=image_url, type="image/jpeg", length="0")
                    fe.media.thumbnail(url=image_url)
                    content_html += f'<p><img src="{image_url}" style="max-width:100%; height:auto;" /></p>'

                content_html += f"<div>{full_body_html}</div>"
                fe.content(content_html, type="CDATA")

            browser.close()
    except Exception as main_err:
        print(f"Playwright encountered a warning: {main_err}")

    fg.rss_file(OUTPUT_FILE, pretty=True)


if __name__ == "__main__":
    build_full_rss()
