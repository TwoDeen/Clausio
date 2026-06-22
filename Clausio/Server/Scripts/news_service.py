import feedparser
import re
import random
from bs4 import BeautifulSoup

# Stable community mirror providing RSS feed for NHK News Web Easy articles
NHK_EASY_RSS_URL = "https://nhkeasier.com/feed/"

def fetch_nhk_news_topics():
    """
    Fetches latest news entries from NHK Web Easy RSS, filters out stories 
    with fewer than 5 sentences, truncates longer summaries to 5, and shuffles the list.
    """
    feed = feedparser.parse(NHK_EASY_RSS_URL)
    topics = []
    
    for entry in feed.entries:
        html_content = entry.get("description", "")
        soup = BeautifulSoup(html_content, "html.parser")
        raw_text = soup.get_text()
        
        # Split paragraph text into individual sentences using the Japanese full-stop
        sentences = [s + "。" for s in raw_text.split("。") if s.strip()]
        
        # 🛑 SKIP: If the story doesn't have enough sentences for a 5x5 board, drop it entirely
        if len(sentences) < 5:
            continue
            
        # ✂️ TRUNCATE: Slice out exactly the first 5 sentences
        truncated_sentences = sentences[:5]
        reconstructed_text = "".join(truncated_sentences)
        
        topics.append({
            "id": entry.get("id", entry.link),
            "title": entry.title,
            "link": entry.link,
            "summary_html": reconstructed_text  
        })
        
    # 🎲 RANDOMIZATION: Shuffle the list of validated stories in-place
    random.shuffle(topics)
    
    return topics

def parse_ruby_html(text_content):
    """
    Parses clean text content strings via RegEx to extract Kanji characters 
    paired directly with their inline Furigana readings.
    """
    # Regex Pattern:
    # ([\u4e00-\u9faf]+) matches 1 or more Kanji characters
    # ([\u3040-\u309f]+) matches 1 or more Hiragana characters directly following it
    pattern = re.compile(r'([\u4e00-\u9faf]+)([\u3040-\u309f]+)')
    
    text_segments = []
    last_idx = 0
    
    # Scan the text string sequentially for Kanji + Furigana pairs
    for match in pattern.finditer(text_content):
        start, end = match.span()
        
        # Pull any plain text leading into this match (like punctuation or particles)
        if start > last_idx:
            plain_chunk = text_content[last_idx:start].strip()
            if plain_chunk:
                text_segments.append({"text": plain_chunk, "furigana": ""})
        
        # Extract capture matching groups
        kanji_text = match.group(1)
        furigana_text = match.group(2)
        
        text_segments.append({
            "text": kanji_text,
            "furigana": furigana_text
        })
        
        last_idx = end
        
    # Catch any remaining trailing punctuation/text segments
    if last_idx < len(text_content):
        remaining_chunk = text_content[last_idx:].strip()
        if remaining_chunk:
            text_segments.append({"text": remaining_chunk, "furigana": ""})
            
    return text_segments

def parse_ruby_html_into_sentences(five_sentences_string):
    """
    Takes a verified 5-sentence string block, splits it into 5 distinct sentence 
    rows, and extracts matched Kanji/Furigana text tokens per row line.
    """
    pattern = re.compile(r'([\u4e00-\u9faf]+)([\u3040-\u309f]+)')
    sentences = [s + "。" for s in five_sentences_string.split("。") if s.strip()]
    
    # Safety slice threshold bounds
    sentences = sentences[:5]
    
    structured_story_rows = []
    
    for sentence in sentences:
        row_tokens = []
        last_idx = 0
        
        for match in pattern.finditer(sentence):
            start, end = match.span()
            if start > last_idx:
                plain_chunk = sentence[last_idx:start].strip()
                if plain_chunk:
                    row_tokens.append({"text": plain_chunk, "furigana": ""})
            
            row_tokens.append({
                "text": match.group(1),
                "furigana": match.group(2)
            })
            last_idx = end
            
        if last_idx < len(sentence):
            remaining_chunk = sentence[last_idx:].strip()
            if remaining_chunk:
                row_tokens.append({"text": remaining_chunk, "furigana": ""})
                
        structured_story_rows.append(row_tokens)
        
    return structured_story_rows # Output: List containing exactly 5 lists of row tokens

if __name__ == "__main__":
    print("Testing NHK News Easy RSS Feed Fetcher (With Sentence Tracking)...")
    try:
        # 1. Test fetching, filtering, and shuffling news headlines
        topics = fetch_nhk_news_topics()
        print(f"Successfully fetched {len(topics)} valid stories from NHK!\n")
        
        if topics:
            # 2. Grab the first story out of the shuffled deck
            first_story = topics[0]
            print(f"--- Randomized Headline Selection: {first_story['title']} ---")
            print(f"Link: {first_story['link']}\n")
            
            story_text = first_story['summary_html']
            print("--- Cleaned 5-Sentence Source Text ---")
            print(f"{story_text}\n")
            
            # 3. Test the updated sentence grouping token parser
            print("Parsing and chunking into 5 distinct row arrays...")
            sentence_rows = parse_ruby_html_into_sentences(story_text)
            
            print(f"Total rows parsed: {len(sentence_rows)} (Should be exactly 5)\n")
            
            # 4. Print structured tokens group-by-group to check preservation mapping
            for idx, row_tokens in enumerate(sentence_rows):
                print(f"--- ROW #{idx + 1} TOKENS ---")
                # Print up to the first 4 tokens in each row layout for visibility
                for segment in row_tokens[:4]:
                    text = segment['text']
                    furigana = segment['furigana']
                    if furigana:
                        print(f"  [Kanji] {text} -> ({furigana})")
                    else:
                        print(f"  [Plain] {text}")
                if len(row_tokens) > 4:
                    print("  ... [truncated display]")
                print()
        else:
            print("No stories met the 5-sentence criteria in the current feed configuration.")
            
    except Exception as e:
        print(f"Test crashed with error: {str(e)}")
