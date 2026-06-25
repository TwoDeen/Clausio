import urllib.request
from bs4 import BeautifulSoup
import feedparser
import random
import re
from playwright.sync_api import sync_playwright

# ── Level → source routing ────────────────────────────────────────────────────

_EASY_LEVELS    = {"N5", "N4"}
_REGULAR_LEVELS = {"N3", "N2", "N1"}

_NHK_EASY_RSS    = "https://nhkeasier.com/feed/"
_NHK_REGULAR_RSS = "https://www3.nhk.or.jp/rss/news/cat0.xml"

_EASY_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# ── Public API ────────────────────────────────────────────────────────────────

def fetch_nhk_news_topics(level: str = "N4") -> list:
    if level.upper().strip() in _REGULAR_LEVELS:
        return _fetch_nhk_regular_topics()
    return _fetch_nhk_easy_topics()

def scrape_article_sentences_and_furigana(url: str):
    if "nhkeasier.com" in url:
        return _scrape_nhk_easy(url)
    if "nhk.or.jp" in url:
        return _scrape_nhk_regular(url)
    return _scrape_nhk_easy(url)


# ── NHK Web Easy  (N5 / N4) ──────────────────────────────────────────────────

def _fetch_nhk_easy_topics() -> list:
    feed   = feedparser.parse(_NHK_EASY_RSS)
    topics = []
    for entry in feed.entries:
        topics.append({
            "id":           entry.get("id", entry.link),
            "title":        entry.title,
            "link":         entry.link,
            "summary_html": "Live fetch required",
        })
    random.shuffle(topics)
    return topics

def _scrape_nhk_easy(url: str):
    url = url.split("?")[0]
    req = urllib.request.Request(url, headers=_EASY_HEADERS)
    with urllib.request.urlopen(req, timeout=10) as response:
        html = response.read().decode("utf-8")

    soup        = BeautifulSoup(html, "html.parser")
    content_div = soup.find("div", class_="entry-content") or soup.find("article") or soup.find("body")

    furigana_dict   = {}
    all_paragraphs  = content_div.find_all("p")
    valid_paragraphs = [p for p in all_paragraphs if p.find("ruby")] or all_paragraphs

    raw_sentences = []
    for p in valid_paragraphs:
        for ruby in p.find_all("ruby"):
            rt = ruby.find("rt")
            if rt:
                reading = rt.get_text().strip()
                rt.decompose()
                kanji = ruby.get_text().strip()
                if kanji:
                    furigana_dict[kanji] = reading
            ruby.replace_with(ruby.get_text().strip())

        text = re.sub(r"\s+", "", p.get_text(separator="", strip=True))
        for sentence in text.split("。"):
            if sentence.strip():
                raw_sentences.append(sentence.strip() + "。")

    final_sentences = _filter_sentences(raw_sentences, min_len=5)
    return final_sentences[:5], furigana_dict


# ── NHK Regular News  (N3 / N2 / N1) ────────────────────────────────────────

def _fetch_nhk_regular_topics() -> list:
    feed   = feedparser.parse(_NHK_REGULAR_RSS)
    topics = []
    for entry in feed.entries[:101010101010101010100]:
        link = entry.get("link", "")
        if not link:
            continue
        topics.append({
            "id":           link,
            "title":        entry.get("title", ""),
            "link":         link,
            "summary_html": "Live fetch required",
        })
    random.shuffle(topics)
    return topics

def _scrape_nhk_regular(url: str):
    clean_text = ""
    url = url.split("?")[0]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ja-JP"
        )
        page = context.new_page()

        try:
            # Wrap goto in a try/except so a VPN lag spike doesn't crash the loop
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                print(f"[NHK Regular] ⚠️ Page load timed out or failed (VPN lag?): {e}")
                return [], {}

            # ── 1. Bypass Multi-Step NHK ONE Consent Wall ──
            wall_indicator = page.locator("text=ご利用にあたって").first
            if wall_indicator.is_visible(timeout=5000):
                print(f"[NHK Regular] 🛡️ NHK ONE wall intercepted. Navigating multi-step consent...")
                
                for step in range(3):
                    checkbox = page.locator("text=内容について確認しました").first
                    if checkbox.is_visible():
                        checkbox.click(force=True)
                        page.wait_for_timeout(1500) 
                    
                    for btn_text in ["次へ", "同意する", "同意して利用する", "利用を開始する", "利用する", "閉じる"]:
                        btn = page.locator(f"text={btn_text}").first
                        if btn.is_visible():
                            print(f"  -> Step {step+1}: Clicking '{btn_text}'")
                            btn.click(force=True)
                            page.wait_for_timeout(3500) 
                            break
                    
                    if not wall_indicator.is_visible():
                        print(f"[NHK Regular] 🛡️ Wall successfully cleared!")
                        # THE REDIRECT FIX: Wait for the post-consent page reload to finish!
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=15000)
                        except Exception:
                            pass
                        break

            # ── 2. Wait for Article to Render ──
            try:
                page.wait_for_selector("article, main, #news_textbody, .content--detail-body, .article-body", timeout=20000)
            except Exception:
                pass
                
            page.wait_for_timeout(3000) 

            # ── NEW: Wrap content extraction in a Retry Loop for heavily delayed redirects ──
            html = ""
            for attempt in range(4):
                try:
                    html = page.content()
                    break  # Successfully grabbed the HTML!
                except Exception as e:
                    if "navigating" in str(e).lower() or "changing the content" in str(e).lower():
                        print(f"  -> ⏳ Caught delayed redirect! Waiting for reload to finish (Attempt {attempt + 1})...")
                        page.wait_for_timeout(3500)
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=10000)
                        except Exception:
                            pass
                    else:
                        print(f"[NHK Regular] ⚠️ Unexpected HTML extraction error: {e}")
                        return [], {}

            if not html:
                print(f"[NHK Regular] ❌ Failed to grab HTML after multiple redirect retries.")
                return [], {}

            # ── 3. Strict Safety Guards ──
            if "ご利用にあたって" in html and "NHK ONEはどなたでも" in html:
                print(f"[NHK Regular] ❌ Wall bypass failed! Stuck on consent screen.")
                return [], {}

            if "For Users Abroad" in html or "intended for viewing in Japan" in html:
                print(f"[NHK Regular] ⚠️ Geoblock detected. Is your Japan VPN on? Skipping.")
                return [], {}

            # ── 4. DOM Parsing ──
            soup = BeautifulSoup(html, "html.parser")

            for tag in soup.find_all(["script", "style", "nav", "aside", "figure", "button", "header", "footer"]):
                tag.decompose()

            body = (
                soup.find(id="news_textbody")                                       or
                soup.find(id="news_article")                                        or
                soup.find("section", class_=re.compile(r"content--detail-body"))   or
                soup.find("div",     class_=re.compile(r"content--detail-body"))   or
                soup.find("div",     class_=re.compile(r"content--body"))          or
                soup.find("div",     class_=re.compile(r"article-body"))           or
                soup.find("div",     class_=re.compile(r"detail-no-js"))           or
                soup.find("div",     class_=re.compile(r"module--detail"))         or
                soup.find("div",     class_=re.compile(r"news_textbody"))          or
                soup.find("div",     class_=re.compile(r"body-text"))              or
                soup.find("article")                                                or
                soup.find("main")
            )

            if body:
                paragraphs = body.find_all("p")
                print(f"  -> [DOM Check] Found {len(paragraphs)} paragraph tags.")
                clean_text = "".join(p.get_text(separator="", strip=True) for p in paragraphs)
            else:
                fallback = soup.find("body")
                print(f"  -> [DOM Check] Fallback body used.")
                clean_text = fallback.get_text(separator="", strip=True) if fallback else ""

        except Exception as e:
            print(f"[NHK Regular] ⚠️ Unexpected Headless browser error on {url}: {e}")
            return [], {}
        finally:
            browser.close()

    clean_text = re.sub(r"\s+", "", clean_text)
    if not clean_text:
        return [], {}

    raw_sentences = [s.strip() + "。" for s in clean_text.split("。") if s.strip()]
    final_sentences = _filter_sentences(raw_sentences, min_len=12)
    return final_sentences[:5], {}


# ── Shared helpers ────────────────────────────────────────────────────────────

def _filter_sentences(sentences: list, min_len: int = 5) -> list:
    return [
        s for s in sentences
        if len(s) > min_len
        and re.search(r"[\u3040-\u309f]", s)
        and not re.search(r"[a-zA-Z]{15,}", s)
        and not re.search(r"[{}[\]_]", s)
        and "…" not in s
        and "？" not in s
        and "！" not in s
    ]

# ── Command-line debug runner ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Testing NHK Regular (N3) Pipeline ===")
    try:
        topics = fetch_nhk_news_topics("N3")
        print(f"✅ Fetched {len(topics)} topics from RSS.")
    except Exception as e:
        print(f"❌ RSS fetch failed: {e}")
        exit(1)

    for i, topic in enumerate(topics[:3]):
        url = topic["link"]
        print(f"\n--- Article {i + 1} ---")
        print(f"Title: {topic.get('title', 'No Title')}")
        print(f"URL  : {url}")
        try:
            sentences, _ = scrape_article_sentences_and_furigana(url)
            print(f"Extracted {len(sentences)} sentences.")
            for idx, s in enumerate(sentences):
                print(f"  {idx + 1}. {s}")
        except Exception as e:
            print(f"❌ Scraper crashed: {e}")
