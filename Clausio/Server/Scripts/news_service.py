import urllib.request
from bs4 import BeautifulSoup
import feedparser
import random
import re

def scrape_article_sentences_and_furigana(url: str):
    """Visits the live webpage and strictly extracts the learning content."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        
    soup = BeautifulSoup(html, "html.parser")
    
    # Locate the main article body safely
    content_div = soup.find("div", class_="entry-content") or soup.find("article") or soup.find("body")
    
    furigana_dict = {}
    
    # 🚀 THE FIX: Target <p> tags, but ONLY those containing <ruby> tags. 
    # This completely ignores sidebars, EPUB download buttons, and footers!
    all_paragraphs = content_div.find_all('p')
    valid_paragraphs = [p for p in all_paragraphs if p.find('ruby') is not None]
    
    # Fallback just in case the format changes
    if not valid_paragraphs:
        valid_paragraphs = all_paragraphs
    
    for p in valid_paragraphs:
        for ruby in p.find_all('ruby'):
            rt = ruby.find('rt')
            if rt:
                reading = rt.get_text().strip()
                rt.decompose() # DESTROY the <rt> tag so it doesn't leak into the main text
                kanji = ruby.get_text().strip()
                if kanji:
                    furigana_dict[kanji] = reading
            
            # Flatten the ruby tag cleanly back into the paragraph
            ruby.replace_with(ruby.get_text().strip())

    # Combine all paragraph text into one block
    clean_text = "".join([p.get_text(separator="", strip=True) for p in valid_paragraphs])
    
    # 🚀 THE FIX: Scrub out any remaining internal whitespace left by the HTML layout
    clean_text = re.sub(r'\s+', '', clean_text)
    
    # Split into sentences and filter out short junk/English text
    raw_sentences = [s + "。" for s in clean_text.split("。") if s.strip()]
            
    # 🚀 THE FIX: Aggressive filtering
    # 1. Must be longer than 5 chars
    # 2. Must contain Japanese characters
    # 3. MUST NOT contain sequences of English letters (blocks the "EPUB" and "Download" junk)
    final_sentences = []
    for s in raw_sentences:
        if len(s) > 5 and re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', s):
            if not re.search(r'[a-zA-Z]{3,}', s): # Reject if it has 3+ English letters in a row
                final_sentences.append(s)
    
    return final_sentences[:5], furigana_dict

def fetch_nhk_news_topics():
    """Fetches the headlines for the SwiftUI menu."""
    feed = feedparser.parse("https://nhkeasier.com/feed/")
    topics = []
    
    for entry in feed.entries:
        topics.append({
            "id": entry.get("id", entry.link),
            "title": entry.title,
            "link": entry.link,
            "summary_html": "Live fetch required" 
        })
        
    random.shuffle(topics)
    return topics
