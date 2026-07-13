import os
import random
import re
import time
import socket
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from typing import Optional, Tuple
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
    site_url: Optional[str] = None
    pdf_url: Optional[str] = None
    author: Optional[str] = None
    article_date: Optional[str] = None
    article_type: Optional[str] = None
    word_level: Optional[int] = None
    sentence_level: Optional[int] = None
    article_length: Optional[int] = None


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

# Use valid Tadoku category pages here.
_CATEGORY_SEEDS = [
    "https://tadoku.info/stories/gendaishakai/",
    "https://tadoku.info/stories/jidou/",
    "https://tadoku.info/stories/chottostories/",
    "https://tadoku.info/stories/taikendan/",
    "https://tadoku.info/stories/eju/",
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


def _is_allowed(url):
    rp = _load_robots()
    if rp is None:
        return True
    try:
        return rp.can_fetch(_HEADERS["User-Agent"], url)
    except Exception:
        return True


def _crawl_delay():
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


def _absolute_url(url):
    return urljoin(_TADOKU_INFO_BASE, url)


def _normalize_text(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _clean_story_title(title):
    title = _normalize_text(title)
    title = re.sub(r"\s*[（(].*?[）)]\s*$", "", title)
    title = re.sub(r"\s*[-–—]\s*(なし|あり)\s*$", "", title)
    return title.strip()


def _cache_path_for_url(url):
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", url)[-150:]
    return os.path.join(_HTML_CACHE_DIR, safe + ".html")


def _fetch_html(url, timeout=12, max_bytes=2_000_000, use_cache=True):
    cache_path = _cache_path_for_url(url)
    if use_cache and os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < _HTML_CACHE_TTL_SECONDS:
            with open(cache_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    if not _is_allowed(url):
        print(" -> [Tadoku] Blocked by robots.txt: {}".format(url))
        return ""

    last_error = None
    for attempt in range(1, _MAX_RETRIES + 1):
        _throttle()
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                chunks = []
                total = 0
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
            print(" -> [Tadoku] Fetch failed (attempt {}/{}) for {}: {}. Backing off {:.1f}s".format(
                attempt, _MAX_RETRIES, url, e, backoff
            ))
            time.sleep(backoff)

    print(" -> [Tadoku] Giving up on {} after {} attempts. Last error: {}".format(
        url, _MAX_RETRIES, last_error
    ))
    return ""


# ---------------------------------------------------------------------------
# Metadata extraction helpers
# ---------------------------------------------------------------------------

def _extract_word_and_sentence_levels(text):
    text = _normalize_text(text)
    text = text.replace("\u3000", " ")

    word_patterns = [
        r"ことばのレベル\s*[:：]?\s*([★☆]{1,5})",
        r"語彙レベル\s*[:：]?\s*([★☆]{1,5})",
    ]
    sentence_patterns = [
        r"ぶんのレベル\s*[:：]?\s*([★☆]{1,5})",
        r"文のレベル\s*[:：]?\s*([★☆]{1,5})",
        r"文レベル\s*[:：]?\s*([★☆]{1,5})",
    ]

    word_level = 0
    sentence_level = 0

    for pattern in word_patterns:
        match = re.search(pattern, text)
        if match:
            word_level = match.group(1).count("★")
            break

    for pattern in sentence_patterns:
        match = re.search(pattern, text)
        if match:
            sentence_level = match.group(1).count("★")
            break

    return word_level, sentence_level


def _extract_article_length(text):
    text = _normalize_text(text)
    match = re.search(r"ながさ\s*[:：]?\s*([0-9]{1,6})\s*じ", text)
    return int(match.group(1)) if match else 0


def _extract_author_and_date(text):
    text = _normalize_text(text)
    match = re.search(
        r"[（(]\s*([0-9]{4}\.[0-9]{2}(?:\.[0-9]{2}|\.XX)?)\s+Written by\s+([^）)]+?)\s*[）)]",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        article_date = match.group(1).strip()
        author = match.group(2).strip()
        return author, article_date
    return None, None


# ---------------------------------------------------------------------------
# Discovery: category page -> story pages -> PDF links
# ---------------------------------------------------------------------------

def discover_story_pages_from_category(category_url):
    html = _fetch_html(category_url, timeout=12)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    story_pages = []
    seen = set()

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

        story_pages.append({
            "title": _clean_story_title(title),
            "link": full_url,
        })
        seen.add(full_url)

    return story_pages


def extract_pdf_links_from_story_page(story_url, default_title=None):
    html = _fetch_html(story_url, timeout=12)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    pdfs = []
    seen = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if ".pdf" not in href.lower():
            continue

        full_url = _absolute_url(href)
        if full_url in seen:
            continue

        label = _normalize_text(a_tag.get_text(" ", strip=True)) or full_url.split("/")[-1]

        container = (
            a_tag.find_parent("li")
            or a_tag.find_parent(["div", "article", "section"])
            or a_tag.parent
        )
        container_text = container.get_text(" ", strip=True) if container else ""

        word_level, sentence_level = _extract_word_and_sentence_levels(container_text)
        article_length = _extract_article_length(container_text)

        pdfs.append({
            "title": label,
            "link": full_url,
            "story_title": default_title,
            "word_level": word_level,
            "sentence_level": sentence_level,
            "article_length": article_length,
        })
        seen.add(full_url)

    return pdfs


def is_furigana_version(link):
    return "_ruby.pdf" in link.lower()


def fetch_tadoku_topics(level="N4"):
    topics = []
    seen_links = set()

    for category_url in _CATEGORY_SEEDS:
        story_pages = discover_story_pages_from_category(category_url)
        print(" -> [Tadoku] Category {}: {} story page(s).".format(category_url, len(story_pages)))

        if story_pages:
            for story in story_pages:
                pdf_items = extract_pdf_links_from_story_page(
                    story["link"],
                    default_title=story["title"],
                )
                for item in pdf_items:
                    link = item["link"]
                    if is_furigana_version(link):
                        continue
                    if link in seen_links:
                        continue

                    seen_links.add(link)
                    base_title = item.get("story_title") or story["title"]
                    title = "{} - {}".format(base_title, item["title"]).strip(" -")

                    topics.append({
                        "id": link,
                        "title": title,
                        "link": link,
                        "word_level": item.get("word_level", 0),
                        "sentence_level": item.get("sentence_level", 0),
                        "article_length": item.get("article_length", 0),
                    })
        else:
            category_title = category_url.rstrip("/").split("/")[-1]
            pdf_items = extract_pdf_links_from_story_page(
                category_url,
                default_title=category_title,
            )
            print(" -> [Tadoku] Category fallback {}: {} PDF item(s) found directly on category page.".format(
                category_url, len(pdf_items)
            ))

            for item in pdf_items:
                link = item["link"]
                if is_furigana_version(link):
                    continue
                if link in seen_links:
                    continue

                seen_links.add(link)
                base_title = item.get("story_title") or category_title
                title = "{} - {}".format(base_title, item["title"]).strip(" -")

                topics.append({
                    "id": link,
                    "title": title,
                    "link": link,
                    "word_level": item.get("word_level", 0),
                    "sentence_level": item.get("sentence_level", 0),
                    "article_length": item.get("article_length", 0),
                })

    random.shuffle(topics)
    print(" -> [Tadoku] Discovered {} PDF topic(s) across {} category page(s).".format(
        len(topics), len(_CATEGORY_SEEDS)
    ))
    return topics


# ---------------------------------------------------------------------------
# Download (step 1) -- always download/cache the PDF before any processing
# ---------------------------------------------------------------------------

def _safe_filename_from_url(url):
    return re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        url.split("/")[-1] or "tadoku_{}.pdf".format(random.randint(1000, 9999)),
    )


def _download_pdf(url, dest_path, timeout=12):
    if not _is_allowed(url):
        print(" -> [Tadoku] robots.txt disallows PDF: {}".format(url))
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
                        print(" -> [Tadoku] Abort download after {} bytes: {}".format(_MAX_PDF_BYTES, url))
                        out_file.close()
                        os.remove(tmp_path)
                        return False

            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < _MIN_VALID_PDF_BYTES:
                print(" -> [Tadoku] Downloaded file too small: {}".format(url))
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                return False

            os.replace(tmp_path, dest_path)
            return True

        except Exception as e:
            last_error = e
            backoff = (2 ** attempt) + random.uniform(0, 1)
            print(" -> [Tadoku] PDF download failed (attempt {}/{}) for {}: {}. Backing off {:.1f}s".format(
                attempt, _MAX_RETRIES, url, e, backoff
            ))
            time.sleep(backoff)

    print(" -> [Tadoku] Giving up on PDF {}. Last error: {}".format(url, last_error))
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    return False


def download_tadoku_pdf(url):
    pdf_url = url.split("?")[0]
    if not pdf_url.lower().endswith(".pdf"):
        return ""

    safe_name = _safe_filename_from_url(pdf_url)
    pdf_path = os.path.join(_DOWNLOAD_DIR, safe_name)

    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) >= _MIN_VALID_PDF_BYTES:
        print(" -> [Tadoku] Reusing cached PDF: {}".format(pdf_path))
        return pdf_path

    print(" -> [Tadoku] Downloading PDF: {}".format(pdf_url))
    ok = _download_pdf(pdf_url, pdf_path, timeout=12)
    return pdf_path if ok else ""


# ---------------------------------------------------------------------------
# Processing (step 2) -- only runs on an already-downloaded local PDF
# ---------------------------------------------------------------------------

def _process_pdf_file(pdf_path):
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
            return [], {}, None, None
        except Exception:
            return [], {}, None, None

    author, article_date = _extract_author_and_date(full_text)

    raw_sentences = []
    text = re.sub(r"\s+", "", full_text)
    for sentence in text.split("。"):
        sentence = sentence.strip()
        if sentence:
            raw_sentences.append(sentence + "。")

    final_sentences = _filter_sentences(raw_sentences, min_len=5)
    return final_sentences[:5], {}, author, article_date


def _filter_sentences(sentences, min_len=5):
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


def scrape_tadoku_sentences_and_furigana(url, topic_metadata=None):
    try:
        pdf_path = download_tadoku_pdf(url)
        meta = topic_metadata or {}

        if not pdf_path:
            return TadokuItem(
                sentences=[],
                furigana={},
                site_url=_TADOKU_INFO_BASE + "/",
                pdf_url=url,
                article_type="story",
                word_level=meta.get("word_level", 0),
                sentence_level=meta.get("sentence_level", 0),
                article_length=meta.get("article_length", 0),
            )

        sentences, furigana_dict, author, article_date = _process_pdf_file(pdf_path)

        return TadokuItem(
            sentences=sentences,
            furigana=furigana_dict,
            site_url=_TADOKU_INFO_BASE + "/",
            pdf_url=url,
            author=author,
            article_date=article_date,
            article_type="story",
            word_level=meta.get("word_level", 0),
            sentence_level=meta.get("sentence_level", 0),
            article_length=meta.get("article_length", 0),
        )

    except Exception as e:
        print(" -> [Tadoku] Failed to download/process PDF: {}".format(e))
        meta = topic_metadata or {}
        return TadokuItem(
            sentences=[],
            furigana={},
            site_url=_TADOKU_INFO_BASE + "/",
            pdf_url=url,
            article_type="story",
            word_level=meta.get("word_level", 0),
            sentence_level=meta.get("sentence_level", 0),
            article_length=meta.get("article_length", 0),
        )


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------

class TadokuProvider:
    SOURCE_ID = "tadoku"
    REQUIRES_VPN = False

    def is_available(self):
        return True

    def fetch_topics(self, level="N4"):
        topics_data = fetch_tadoku_topics(level)
        return [
            TadokuTopic(
                id=t["id"],
                title=t["title"],
                link=t["link"],
                metadata={
                    "word_level": t.get("word_level", 0),
                    "sentence_level": t.get("sentence_level", 0),
                    "article_length": t.get("article_length", 0),
                },
            )
            for t in topics_data
        ]

    def fetch_sentences(self, topic):
        return scrape_tadoku_sentences_and_furigana(
            topic.link,
            getattr(topic, "metadata", {}),
        )
