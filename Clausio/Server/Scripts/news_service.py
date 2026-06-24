import urllib.request
from bs4 import BeautifulSoup
import feedparser
import random
import re

# ── Level → source routing ────────────────────────────────────────────────────

_EASY_LEVELS    = {"N5", "N4"}          # nhkeasier.com — learner register
_REGULAR_LEVELS = {"N3", "N2", "N1"}   # www3.nhk.or.jp — native register

_NHK_EASY_RSS    = "https://nhkeasier.com/feed/"
_NHK_REGULAR_RSS = "https://www3.nhk.or.jp/rss/news/cat0.xml"

# ── Public API ───────────────────────────────────────────────────────────────

def fetch_nhk_news_topics(level: str = "N4") -> list:
    """Returns topic list from the source appropriate for the requested level.
       N5/N4 → NHK Web Easy   |   N3/N2/N1 → NHK Regular News
    """
    if level.upper().strip() in _REGULAR_LEVELS:
        return _fetch_nhk_regular_topics()
    return _fetch_nhk_easy_topics()


def scrape_article_sentences_and_furigana(url: str):
    """Routes to the correct scraper based on the article URL.
       nhkeasier.com URLs → Easy scraper (with furigana)
       nhk.or.jp URLs     → Regular scraper (no furigana)
    """
    if "nhkeasier.com" in url:
        return _scrape_nhk_easy(url)
    if "nhk.or.jp" in url:
        return _scrape_nhk_regular(url)
    return _scrape_nhk_easy(url)  # safe fallback


# ── NHK Web Easy  (N5 / N4) ──────────────────────────────────────────────────

def _fetch_nhk_easy_topics() -> list:
    feed = feedparser.parse(_NHK_EASY_RSS)
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
    """Extracts sentences + furigana from an NHK Web Easy article."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        html = response.read().decode("utf-8")

    soup = BeautifulSoup(html, "html.parser")
    content_div = (
        soup.find("div", class_="entry-content") or
        soup.find("article") or
        soup.find("body")
    )

    furigana_dict = {}
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

        text = p.get_text(separator="", strip=True)
        text = re.sub(r"\s+", "", text)
        
        for sentence in text.split("。"):
            if sentence.strip():
                raw_sentences.append(sentence.strip() + "。")

    final_sentences = [
        s for s in raw_sentences
        if len(s) > 5
        and re.search(r"[\u3040-\u309f]", s)      # MUST contain at least one Hiragana character
        and not re.search(r"[a-zA-Z]{15,}", s)
        and "…" not in s
        and "？" not in s
        and "！" not in s
    ]
    return final_sentences[:5], furigana_dict


# ── NHK Regular News  (N3 / N2 / N1) ────────────────────────────────────────

def _fetch_nhk_regular_topics() -> list:
    """Fetches headlines from NHK regular news RSS (general/top category)."""
    feed = feedparser.parse(_NHK_REGULAR_RSS)
    topics = []
    for entry in feed.entries[:30]:
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
    """Extracts sentences from a full NHK regular news article (no furigana)."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        html = response.read().decode("utf-8")

    soup = BeautifulSoup(html, "html.parser")

    # Target specific NHK text containers first to avoid sidebars naturally
    containers = soup.find_all(class_=re.compile(r"content--(detail|summary|body)"))
    if not containers:
        main_area = soup.find("article") or soup.find("main") or soup.find("body")
        containers = [main_area] if main_area else []

    # Aggressively delete noise blocks (related articles, rankings, share buttons, timestamps)
    for c in containers:
        for noise in c.find_all(["script", "style", "nav", "aside", "figure", "button", "time"]):
            noise.decompose()
        for noise in c.find_all(class_=re.compile(r"related|ranking|sns|share|link|footer|date", re.I)):
            noise.decompose()

    paragraphs = []
    for c in containers:
        paragraphs.extend(c.find_all("p"))
        
    # If no <p> tags remain, try raw text extraction on the containers as a last resort
    if not paragraphs:
        for c in containers:
            text = c.get_text(separator="。", strip=True)
            paragraphs.append(BeautifulSoup(f"<p>{text}</p>", "html.parser").p)

    raw_sentences = []
    for p in paragraphs:
        text = p.get_text(separator="", strip=True)
        text = re.sub(r"\s+", "", text)
        
        for sentence in text.split("。"):
            if sentence.strip():
                raw_sentences.append(sentence.strip() + "。")

    # The ultimate filtering gauntlet
    final_sentences = [
        s for s in raw_sentences
        if len(s) > 12                            # Avoid micro-fragments
        and re.search(r"[\u3040-\u309f]", s)      # MUST contain at least one Hiragana character (blocks dates)
        and not re.search(r"[a-zA-Z]{15,}", s)    # Blocks base64/JS noise
        and not re.search(r"[{}[\]_]", s)         # Drops stray JSON/JS code artifacts
        and "…" not in s                          # Drops incomplete teaser sentences
        and "？" not in s                         # Drops sidebar navigation questions
        and "！" not in s                         # Drops clickbait sidebar exclamations
    ]
    
    return final_sentences[:5], {}
    
# ── Command Line Debugging ───────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Testing NHK Regular (N3) Pipeline ===")
    
    # 1. Fetch the topics
    try:
        topics = fetch_nhk_news_topics("N3")
        print(f"✅ Successfully fetched {len(topics)} topics from RSS.")
    except Exception as e:
        print(f"❌ Failed to fetch RSS: {e}")
        exit(1)

    # 2. Try scraping the first 3 articles to see what happens
    for i, topic in enumerate(topics[:3]):
        url = topic['link']
        print(f"\n--- Article {i+1} ---")
        print(f"Title: {topic.get('title', 'No Title')}")
        print(f"URL:   {url}")
        
        try:
            sentences, furigana = scrape_article_sentences_and_furigana(url)
            print(f"Extracted {len(sentences)} valid sentences.")
            
            if len(sentences) > 0:
                for idx, s in enumerate(sentences):
                    print(f"  {idx+1}. {s}")
            else:
                print("⚠️ WARNING: 0 sentences extracted. The DOM parser failed or regex stripped everything.")
                
        except Exception as e:
            print(f"❌ Scraper crashed on this URL: {e}")
