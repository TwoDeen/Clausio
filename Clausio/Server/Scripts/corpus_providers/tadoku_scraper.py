import os
import random
import re
import time
import socket
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import fitz  # PyMuPDF

socket.setdefaulttimeout(12)


@dataclass
class TadokuTopic:
    id: str
    title: str
    link: str
    metadata: dict = field(default_factory=dict)


@dataclass
class TadokuItem:
    sentences: list
    furigana: dict


_TADOKU_INFO_BASE = "https://tadoku.info"
_STORIES_INDEX_URL = "https://tadoku.info/stories/"
_ROBOTS_URL = "https://tadoku.info/robots.txt"

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DOWNLOAD_DIR = os.path.join(_BASE_DIR, "tadoku_downloads")
_HTML_CACHE_DIR = os.path.join(_BASE_DIR, "tadoku_html_cache")
os.makedirs(_DOWNLOAD_DIR, exist_ok=True)
os.makedirs(_HTML_CACHE_DIR, exist_ok=True)

_HEADERS = {
    "User-Agent": "TadokuCorpusBot/1.0 (+contact: your-email@example.com; personal research scraper)"
}

# Seed category pages to crawl for topics/PDFs. Add more category slugs here
# as needed (each maps to https://tadoku.info/stories/<slug>/).
_CATEGORY_SEEDS = [
    "https://tadoku.info/stories/gendaishakai/",
]

_MAX_PDF_BYTES = 6 * 1024 * 1024
_MIN_VALID_PDF_BYTES = 2048

_MIN_DELAY_SECONDS = 2.0
_MAX_DELAY_SECONDS = 4.0
_MAX_RETRIES = 3
_HTML_CACHE_TTL_SECONDS = 60 * 60 * 24  # 24h

_robot_parser = None
_last_request_time = 0.0


# ---------------------------------------------------------------------------
# Politeness helpers: robots.txt compliance + throttling + retries
# ---------------------------------------------------------------------------

def _load_robots():
    global _robot_parser
    if _robot_parser is not None:
        return _robot_parser
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(_ROBOTS_URL)
        rp.read()
    except Exception:
        rp = None
    _robot_parser = rp
    return rp


def _is_allowed(url: str) -> bool:
    rp = _load_robots()
    if rp is None:
        return True
    try:
        return rp.can_fetch(_HEADERS["User-Agent"], url)
    except Exception:
        return True


def _crawl_delay() -> float:
    rp = _load_robots()
    if rp is None:
        return _MIN_DELAY_SECONDS
    try:
        delay = rp.crawl_delay(_HEADERS["User-Agent"])
        if delay:
            return max(float(delay), _MIN_DELAY_SECONDS)
    except Exception:
        pass
    return _MIN_DELAY_SECONDS


def _throttle():
    global _last_request_time
    min_gap = _crawl_delay()
    elapsed = time.time() - _last_request_time
    wait = max(0.0, min_gap - elapsed) + random.uniform(0, _MAX_DELAY_SECONDS - _MIN_DELAY_SECONDS)
    if wait > 0:
        time.sleep(wait)
    _last_request_time = time.time()


def _absolute_url(url: str) -> str:
    return urljoin(_TADOKU_INFO_BASE, url)


def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _cache_path_for_url(url: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", url)[-150:]
    return os.path.join(_HTML_CACHE_DIR, safe + ".html")


def _fetch_html(url: str, timeout: int = 12, max_bytes: int = 2_000_000, use_cache: bool = True) -> str:
    cache_path = _cache_path_for_url(url)
    if use_cache and os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < _HTML_CACHE_TTL_SECONDS:
            with open(cache_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    if not _is_allowed(url):
        print(f" -> [Tadoku] Blocked by robots.txt: {url}")
        return ""

    last_error = None
    for attempt in range(1, _MAX_RETRIES + 1):
        _throttle()
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                chunks, total = [], 0
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= max_bytes:
                        break
                html = b"".join(chunks).decode("utf-8", errors="ignore")

            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(html)
            return html

        except Exception as e:
            last_error = e
            backoff = (2 ** attempt) + random.uniform(0, 1)
            print(f" -> [Tadoku] Fetch failed (attempt {attempt}/{_MAX_RETRIES}) for {url}: {e}. Backing off {backoff:.1f}s")
            time.sleep(backoff)

    print(f" -> [Tadoku] Giving up on {url} after {_MAX_RETRIES} attempts. Last error: {last_error}")
    return ""


# ---------------------------------------------------------------------------
# Discovery: category page -> story pages -> PDF links
# ---------------------------------------------------------------------------

def discover_story_pages_from_category(category_url: str) -> list:
    html = _fetch_html(category_url, timeout=12)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    story_pages, seen = [], set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        full_url = _absolute_url(href)
        if not full_url.startswith(category_url):
            continue
        if full_url == category_url or full_url in seen:
            continue
        title = _normalize_text(a_tag.get_text(" ", strip=True))
        if not title:
            continue
        story_pages.append({"title": title, "link": full_url})
        seen.add(full_url)

    return story_pages


def extract_pdf_links_from_story_page(story_url: str) -> list:
    html = _fetch_html(story_url, timeout=12)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    pdfs, seen = [], set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if ".pdf" not in href.lower():
            continue
        full_url = _absolute_url(href)
        if full_url in seen:
            continue
        label = _normalize_text(a_tag.get_text(" ", strip=True)) or full_url.split("/")[-1]
        pdfs.append({"title": label, "link": full_url})
        seen.add(full_url)

    return pdfs


def is_furigana_version(link: str) -> bool:
    """Ruby/furigana PDFs are suffixed with '_ruby.pdf' and labeled あり."""
    return "_ruby.pdf" in link.lower()


def fetch_tadoku_topics(level: str = "N4") -> list:
    """Crawl the seeded category pages and return one topic per non-ruby PDF
    found. `level` is accepted for interface compatibility but tadoku.info
    stories aren't tagged by JLPT level, so all discovered topics are returned."""
    topics = []
    seen_links = set()

    for category_url in _CATEGORY_SEEDS:
        story_pages = discover_story_pages_from_category(category_url)
        print(f" -> [Tadoku] Category {category_url}: {len(story_pages)} story page(s).")

        for story in story_pages:
            pdf_items = extract_pdf_links_from_story_page(story["link"])
            for item in pdf_items:
                link = item["link"]
                if is_furigana_version(link):
                    continue  # skip ruby/furigana duplicates by default
                if link in seen_links:
                    continue
                seen_links.add(link)
                title = f"{story['title']} - {item['title']}".strip(" -")
                topics.append({"id": link, "title": title, "link": link})

    random.shuffle(topics)
    print(f" -> [Tadoku] Discovered {len(topics)} PDF topic(s) across {len(_CATEGORY_SEEDS)} category page(s).")
    return topics


# ---------------------------------------------------------------------------
# Download (step 1) -- always download/cache the PDF before any processing
# ---------------------------------------------------------------------------

def _safe_filename_from_url(url: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("/")[-1] or f"tadoku_{random.randint(1000,9999)}.pdf")


def _download_pdf(url: str, dest_path: str, timeout: int = 12) -> bool:
    if not _is_allowed(url):
        print(f" -> [Tadoku] robots.txt disallows PDF: {url}")
        return False

    tmp_path = dest_path + ".part"
    last_error = None

    for attempt in range(1, _MAX_RETRIES + 1):
        _throttle()
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as response, open(tmp_path, "wb") as out_file:
                total = 0
                while True:
                    chunk = response.read(32768)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    total += len(chunk)
                    if total > _MAX_PDF_BYTES:
                        print(f" -> [Tadoku] Abort download after {_MAX_PDF_BYTES} bytes: {url}")
                        out_file.close()
                        os.remove(tmp_path)
                        return False

            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < _MIN_VALID_PDF_BYTES:
                print(f" -> [Tadoku] Downloaded file too small: {url}")
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                return False

            os.replace(tmp_path, dest_path)
            return True

        except Exception as e:
            last_error = e
            backoff = (2 ** attempt) + random.uniform(0, 1)
            print(f" -> [Tadoku] PDF download failed (attempt {attempt}/{_MAX_RETRIES}) for {url}: {e}. Backing off {backoff:.1f}s")
            time.sleep(backoff)

    print(f" -> [Tadoku] Giving up on PDF {url}. Last error: {last_error}")
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    return False


def download_tadoku_pdf(url: str) -> str:
    """Step 1: ensure the PDF is downloaded locally (cached) and return its
    local file path, or empty string on failure."""
    pdf_url = url.split("?")[0]
    if not pdf_url.lower().endswith(".pdf"):
        return ""

    safe_name = _safe_filename_from_url(pdf_url)
    pdf_path = os.path.join(_DOWNLOAD_DIR, safe_name)

    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) >= _MIN_VALID_PDF_BYTES:
        print(f" -> [Tadoku] Reusing cached PDF: {pdf_path}")
        return pdf_path

    print(f" -> [Tadoku] Downloading PDF: {pdf_url}")
    ok = _download_pdf(pdf_url, pdf_path, timeout=12)
    return pdf_path if ok else ""


# ---------------------------------------------------------------------------
# Processing (step 2) -- only runs on an already-downloaded local PDF
# ---------------------------------------------------------------------------

def _process_pdf_file(pdf_path: str):
    full_text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        full_text += page.get_text("text") + "\n"
    doc.close()

    if len(full_text.strip()) < 10:
        try:
            import pytesseract
            from pdf2image import convert_from_path
            pages = convert_from_path(pdf_path)
            full_text = ""
            for page in pages:
                full_text += pytesseract.image_to_string(page, lang="jpn") + "\n"
        except ImportError:
            return [], {}
        except Exception:
            return [], {}

    raw_sentences = []
    text = re.sub(r"\s+", "", full_text)
    for sentence in text.split("。"):
        sentence = sentence.strip()
        if sentence:
            raw_sentences.append(sentence + "。")

    final_sentences = _filter_sentences(raw_sentences, min_len=5)
    return final_sentences[:5], {}


def _filter_sentences(sentences: list, min_len: int = 5) -> list:
    return [
        s
        for s in sentences
        if len(s) > min_len
        and re.search(r"[\u3040-\u309f]", s)
        and not re.search(r"[a-zA-Z]{15,}", s)
        and not re.search(r"[{}\[\]_]", s)
        and "…" not in s
        and "？" not in s
        and "！" not in s
    ]


def scrape_tadoku_sentences_and_furigana(url: str):
    """Matches the old function signature/behavior exactly: downloads the
    PDF first (step 1), then processes it into sentences (step 2)."""
    try:
        pdf_path = download_tadoku_pdf(url)
        if not pdf_path:
            return [], {}
        return _process_pdf_file(pdf_path)
    except Exception as e:
        print(f" -> [Tadoku] Failed to download/process PDF: {e}")
        return [], {}


# ---------------------------------------------------------------------------
# Provider interface -- identical shape to the old tadoku_scraper.py
# ---------------------------------------------------------------------------

class TadokuProvider:
    SOURCE_ID = "tadoku"
    REQUIRES_VPN = False

    def is_available(self) -> bool:
        return True

    def fetch_topics(self, level: str = "N4") -> list:
        topics_data = fetch_tadoku_topics(level)
        return [TadokuTopic(id=t["id"], title=t["title"], link=t["link"]) for t in topics_data]

    def fetch_sentences(self, topic) -> TadokuItem:
        sentences, furigana_dict = scrape_tadoku_sentences_and_furigana(topic.link)
        return TadokuItem(sentences=sentences, furigana=furigana_dict)
