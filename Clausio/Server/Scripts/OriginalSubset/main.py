import asyncio
from typing import List
from urllib.parse import urljoin
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from bs4 import XMLParsedAsHTMLWarning
import warnings
import os

# --------------------------------------------------------------------------
# 1. FastAPI App Initialization & CORS Configuration
# --------------------------------------------------------------------------
warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)
app = FastAPI(title="Aozora Caching API (Miyazawa Kenji Edition)", version="1.3.0")

origins = [
    "http://localhost:3000",
    os.getenv("FRONTEND_URL") 
]
origins = [origin for origin in origins if origin]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# 2. Load and Filter CSV Dataset (Restricted to Miyazawa Kenji)
# --------------------------------------------------------------------------
print("Loading catalog dataset...")
df = pd.read_csv("list_person_all_extended.csv", encoding="cp932")

# Only keep entries that have a valid HTML/XHTML file link
df = df.dropna(subset=['XHTML/HTMLファイルURL'])

# Strictly filter database records for Miyazawa Kenji
df = df[(df['姓'] == '宮沢') & (df['名'] == '賢治')]
print(f"Dataset ready. Loaded {len(df)} available works by Miyazawa Kenji.")

# --------------------------------------------------------------------------
# 3. Data Storage Schemas (Pydantic Models)
# --------------------------------------------------------------------------
class NovelData:
    def __init__(self, name: str, author: str, content: str, url: str):
        self.name = name
        self.author = author
        self.content = content
        self.url = url

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str

class SearchResult(BaseModel):
    name: str
    author: str
    content: str
    url: str

# Global Memory Queue Cache
novel_cache: List[NovelData] = []
CACHE_MAX_SIZE = 20

# --------------------------------------------------------------------------
# 4. Core Downloader, Parser & Text Cleaner Logic
# --------------------------------------------------------------------------
def fetch_and_process_novel() -> NovelData:
    if df.empty:
        return None
        
    # Sample a random masterpiece row from the filtered Miyazawa Kenji list
    random_row = df.sample(n=1).iloc[0]
    title = random_row['作品名']
    author = f"{random_row['姓']} {random_row['名']}"
    url = random_row['XHTML/HTMLファイルURL']
    
    try:
        response = requests.get(url, timeout=10)
        # Handle Shift_JIS encoding format natively used by Aozora Bunko
        response.encoding = 'shift_jis'
        
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Decompose Furigana/Rubies metadata tags (keeps text strings clean)
        for rt in soup.find_all(['rt', 'rp']):
            rt.decompose()
            
        # Extract novel body content out of Aozora's standard content container
        main_text_div = soup.find(class_='main_text')
        if main_text_div:
            raw_content = main_text_div.get_text()
        else:
            raw_content = soup.get_text()
            
        # Clean formatting, stray white-spaces, or broken artifacts
        cleaned_content = raw_content.strip()
        cleaned_content = re.sub(r'\r\n', '\n', cleaned_content)
        
        return NovelData(name=title, author=author, content=cleaned_content, url=url)
        
    except Exception as e:
        print(f"Error downloading {title}: {e}")
        return None

# --------------------------------------------------------------------------
# 5. Asynchronous Internal Caching Loop
# --------------------------------------------------------------------------
async def replenish_cache():
    while True:
        if len(novel_cache) < CACHE_MAX_SIZE:
            # Shift CPU/Network bound requests over to a secondary runtime thread
            novel = await asyncio.to_thread(fetch_and_process_novel)
            if novel:
                novel_cache.append(novel)
                print(f"キャッシュ補充中... (現在 {len(novel_cache)}/{CACHE_MAX_SIZE} 件: 「{novel.name}」)")
        
        # Idle briefly between actions to keep thread cycles resting smoothly
        await asyncio.sleep(1)

# --------------------------------------------------------------------------
# 6. Lifecycle Event Directives
# --------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    print("Application Server active. Building Kenji Miyazawa content queues...")
    asyncio.create_task(replenish_cache())

# --------------------------------------------------------------------------
# 7. Restful API Endpoints
# --------------------------------------------------------------------------
@app.get("/", response_model=HealthResponse, summary="Server Health Status")
def health_check():
    return HealthResponse(status="healthy", timestamp=datetime.now(), version="1.3.0")

@app.get("/search", response_model=SearchResult, summary="Get cached Miyazawa Kenji novel segment")
async def get_cached_novel_intro(num_chars: int = Query(200, gt=-2, le=500000, description="Set to -1 for the full story text")):
    # Fallback to direct network scrape if local queue hasn't compiled yet
    if not novel_cache:
        print("Cache queue cold. Executing a fallback live network lookup...")
        novel = await asyncio.to_thread(fetch_and_process_novel)
        if not novel:
            raise HTTPException(status_code=503, detail="Failed to fetch any content from Aozora server records.")
    else:
        # Retrieve the earliest story from queue
        novel = novel_cache.pop(0)

    content = novel.content
    
    # Check if the full story text was requested
    if num_chars == -1:
        display_text = content
    else:
        if len(content) > num_chars:
            display_text = content[:num_chars] + "..."
        else:
            display_text = content

    return SearchResult(
        name=novel.name,
        author=novel.author,
        content=display_text,
        url=novel.url
    )
