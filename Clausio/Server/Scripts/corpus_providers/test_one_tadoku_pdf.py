import os
import re
import urllib.request
import fitz

PDF_URL = "https://tadoku.info/wp-content/uploads/2021/11/taxidenonichijoukaiwa.pdf"
PDF_PATH = "taxidenonichijoukaiwa.pdf"


def normalize_text(s):
    return re.sub(r"\s+", " ", s or "").strip()


def download_pdf(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        return path

    req = urllib.request.Request(url, headers={
        "User-Agent": "TadokuCorpusBot/1.0 (+contact: your-email@example.com; personal research scraper)"
    })
    with urllib.request.urlopen(req, timeout=20) as response, open(path, "wb") as f:
        f.write(response.read())
    return path


def looks_like_tadoku_stamp_line(line):
    line = normalize_text(line)
    if not line:
        return False

    patterns = [
        r"^たどくのひろば",
        r"^http://tadoku\.info",
        r"^https://tadoku\.info",
        r"^tadoku\.info",
    ]
    return any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in patterns)


def remove_tadoku_corner_stamp(text):
    patterns = [
        r"たどくのひろば\s*https?://tadoku\.info",
        r"たどくのひろば\s*http://tadoku\.info",
        r"たどくのひろば\s*tadoku\.info",
        r"http://tadoku\.info",
        r"https://tadoku\.info",
    ]
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned


def body_clip_rect(page):
    rect = page.rect
    top_margin = rect.height * 0.12
    bottom_margin = rect.height * 0.12

    return fitz.Rect(
        rect.x0,
        rect.y0 + top_margin,
        rect.x1,
        rect.y1 - bottom_margin
    )


def clean_ocr_text(text):
    lines = []
    for line in text.splitlines():
        line = normalize_text(line)
        if not line:
            continue
        if looks_like_tadoku_stamp_line(line):
            continue
        if re.fullmatch(r"\d{1,3}", line):
            continue
        lines.append(line)
    return "\n".join(lines)


def filter_sentences(sentences, min_len=5):
    return [
        s for s in sentences
        if len(s) > min_len
        and re.search(r"[\u3040-\u309f]", s)
        and not re.search(r"[a-zA-Z]{15,}", s)
        and not re.search(r"[{}\[\]_]", s)
        and "…" not in s
        and "？" not in s
        and "！" not in s
    ]


def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    parts = []

    for i, page in enumerate(doc):
        raw_text = page.get_text("text", sort=True)

        clip = body_clip_rect(page)
        clipped_text = page.get_text("text", clip=clip, sort=True)
        cleaned = remove_tadoku_corner_stamp(clipped_text)
        parts.append(cleaned)

        print(f"\n--- PAGE {i + 1} RAW PAGE TEXT PREVIEW ---")
        print(raw_text[:700])

        print(f"\n--- PAGE {i + 1} BODY-CLIPPED TEXT PREVIEW ---")
        print(clipped_text[:700])

        print(f"\n--- PAGE {i + 1} CLEANED TEXT PREVIEW ---")
        print(cleaned[:700])

    doc.close()

    full_text = "\n".join(parts)
    full_text = remove_tadoku_corner_stamp(full_text)
    return full_text

def ocr_test_crop(pdf_image):
    width, height = pdf_image.size
    top_crop = int(height * 0.12)
    bottom_crop = int(height * 0.12)
    return pdf_image.crop((0, top_crop, width, height - bottom_crop))

def main():
    pdf_path = download_pdf(PDF_URL, PDF_PATH)
    full_text = extract_text(pdf_path)

    print("\n===== CORNER-STAMP CHECK =====")
    leak_lines = [
        line for line in full_text.splitlines()
        if "たどく" in line.lower() or "tadoku" in line.lower()
    ]
    if leak_lines:
        print("Potential leaked lines:")
        for line in leak_lines:
            print(line)
    else:
        print("No tadoku corner-stamp text found.")

    text = re.sub(r"\s+", "", full_text)
    text = remove_tadoku_corner_stamp(text)

    raw_sentences = []
    for sentence in text.split("。"):
        sentence = sentence.strip()
        if sentence:
            raw_sentences.append(sentence + "。")

    final_sentences = filter_sentences(raw_sentences, min_len=5)

    print("\n===== FINAL SENTENCES =====")
    for i, sentence in enumerate(final_sentences[:20], 1):
        print(f"{i}. {sentence}")


if __name__ == "__main__":
    main()
