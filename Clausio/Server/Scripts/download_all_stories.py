import os
import re
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup

def download_kenji_stories(csv_path="list_person_all_extended.csv", output_dir="miyazawa_kenji_stories"):
    # 1. Create a dedicated folder to save the stories cleanly
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: '{output_dir}'")

    # 2. Load the dataset with the safe encoding extension we found
    print("Reading catalog dataset...")
    try:
        # Trying cp932/utf-8-sig extensions to prevent crashing on rare symbols
        df = pd.read_csv(csv_path, encoding="cp932")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # 3. Filter strictly for available HTML files by Miyazawa Kenji
    df = df.dropna(subset=['XHTML/HTMLファイルURL'])
    df = df[(df['姓'] == '宮沢') & (df['名'] == '賢治')]
    
    total_stories = len(df)
    print(f"Found {total_stories} total works available by Miyazawa Kenji. Starting download sequence...\n")

    # 4. Loop through every single row item and fetch it
    for index, row in df.iterrows():
        title = row['作品名']
        author = f"{row['姓']}{row['名']}"
        url = row['XHTML/HTMLファイルURL']
        
        # Strip out any symbols like slashes or question marks that OS filesystems ban in file names
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        filename = os.path.join(output_dir, f"{safe_title}_{author}.txt")
        
        # Skip downloading if the file already exists (handy if the process gets interrupted)
        if os.path.exists(filename):
            print(f"[{index + 1}/{total_stories}] Skipping '{title}' (Already downloaded).")
            continue

        print(f"[{index + 1}/{total_stories}] Downloading: '{title}'...")
        
        try:
            # Fetch raw web documents
            response = requests.get(url, timeout=10)
            response.encoding = 'shift_jis' # Aozora text payloads use Shift_JIS mapping
            
            if response.status_code != 200:
                print(f"       --> Failed to download (HTTP status code {response.status_code})")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Decompose Ruby markup tags to clean out formatting/furigana
            for rt in soup.find_all(['rt', 'rp']):
                rt.decompose()
                
            # Isolate the core text container element
            main_text_div = soup.find(class_='main_text')
            if main_text_div:
                raw_text = main_text_div.get_text()
            else:
                raw_text = soup.get_text()
                
            cleaned_text = raw_text.strip()
            cleaned_text = re.sub(r'\r\n', '\n', cleaned_text)
            
            # Save data out to its own uniquely named separate text file
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Title: {title}\n")
                f.write(f"Author: {row['姓']} {row['名']}\n")
                f.write(f"Source URL: {url}\n")
                f.write("-" * 50 + "\n\n")
                f.write(cleaned_text)
                
            # Polite pause: rest 1 second between requests to not overwhelm Aozora Bunko's servers
            time.sleep(1)
            
        except Exception as e:
            print(f"       --> Error encountered while downloading '{title}': {e}")

    print(f"\nAll downloads finished! Check the '{output_dir}' directory on your computer.")

if __name__ == "__main__":
    download_kenji_stories()
