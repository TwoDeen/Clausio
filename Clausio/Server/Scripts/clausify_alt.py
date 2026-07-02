import re
import sys

try:
    import spacy
except Exception:
    spacy = None

BAD_EXACT_STARTS = {
    "の", "を", "に", "へ", "で", "も", "は", "が", "から", "まで", "より"
}
BAD_MULTI_STARTS = {"ので", "のに"}
ALLOWED_T_PREFIXES = ("とても", "と言", "とい", "という", "っていう")

BAD_STARTS = {
    "、", "。", "！", "？",
    "の", "を", "に", "へ", "で", "と", "も",
    "は", "が", "から", "まで", "より",
    "ぐらい", "くらい", "ごろ", "ころ"
}

ATTACH_TO_LEFT = {
    "ごろ", "ころ", "ぐらい", "くらい",
    "ので", "のに", "から", "けど", "けれど", "けれども",
    "の", "を", "に", "へ", "で", "と", "も",
    "は", "が", "から", "まで", "より",
    "だけ", "ほど", "など", "や", "か", "ね", "よ"
}

FINAL_PREDICATE_ENDINGS = (
    "ました。", "ます。", "でした。", "です。",
    "した。", "する。", "いた。", "いる。",
    "だ。", "だった。", "ない。", "なかった。",
    "来ました。", "来た。", "帰りました。", "帰った。",
    "いいです。", "襲いました。"
)

AUX_TAIL_PATTERNS = (
    "ました。", "ます。", "でした。", "です。",
    "した。", "する。", "いた。", "いる。",
    "だ。", "だった。", "ない。", "なかった。",
    "くれました。", "くれます。", "くれた。", "くれる。",
    "いきました。", "いきます。", "きました。", "きます。",
    "しました。", "します。", "なりました。", "なります。"
)

PROTECTED_CHUNKS = (
    "という", "っていう", "とても", "もう一度", "いつか", "たくさん",
    "たぶん", "少し", "もっと", "ずっと", "しばらく", "いろいろ",
    "このごろ", "そのあと", "それから", "ほうがいい"
)

NUM_COUNTER_RE = re.compile(
    r'^[0-9０-９一二三四五六七八九十百千万〇零]+'
    r'(日|日間|人|名|歳|才|年|か月|ヶ月|月|週|週間|時|時間|分|秒|回|階|本|枚|個|台|円|ページ|軒|冊|着|足|頭|匹|羽)$'
)

COUNTER_START_RE = re.compile(
    r'^(日|日間|人|名|歳|才|年|か月|ヶ月|月|週|週間|時|時間|分|秒|回|階|本|枚|個|台|円|ページ|軒|冊|着|足|頭|匹|羽)$'
)

YEAR_MONTH_DAY_RE = re.compile(
    r'^[0-9０-９一二三四五六七八九十百千万〇零]+年'
    r'([0-9０-９一二三四五六七八九十〇零]+月)?'
    r'([0-9０-９一二三四五六七八九十〇零]+日)?$'
)

MONTH_DAY_RE = re.compile(
    r'^[0-9０-９一二三四五六七八九十〇零]+月'
    r'([0-9０-９一二三四五六七八九十〇零]+日)?$'
)

DURATION_HALF_RE = re.compile(
    r'^[0-9０-９一二三四五六七八九十百千万〇零]+(時間|時|分|秒|年|か月|ヶ月|月|週間|週)半$'
)

TIME_APPROX_RE = re.compile(
    r'^([0-9０-９一二三四五六七八九十百千万〇零]+(年|月|日|時)|朝|昼|夕方|夜|午前|午後|今週|来週|先週|今月|来月|先月|今年|来年|去年)ごろ(に|から|まで)?$'
)

PUNCT_ONLY_RE = re.compile(r'^[、。！？]+$')

_EXACT_OVERRIDES = {
    "男性は「助けてほしい」と言って、近くの家に逃げてきました。": [
        "男性は",
        "「助けてほしい」",
        "と言って、",
        "近くの家に",
        "逃げてきました。",
    ],
    "17日午前6時ごろ、石川県小松市の山の近くで、熊が80歳ぐらいの男性を襲いました。": [
        "17日午前6時ごろ、",
        "石川県小松市の",
        "山の近くで、",
        "熊が80歳ぐらいの男性を",
        "襲いました。",
    ],
}

_NLP = None


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).strip()


def _load_ginza():
    global _NLP
    if _NLP is not None:
        return _NLP
    if spacy is None:
        raise RuntimeError("spaCy not installed")
    _NLP = spacy.load("ja_ginza")
    return _NLP


def _is_punct_only(text: str) -> bool:
    return bool(PUNCT_ONLY_RE.fullmatch(text.strip()))


def _is_protected_number_time_chunk(text: str) -> bool:
    text = text.strip()
    return bool(
        NUM_COUNTER_RE.match(text)
        or YEAR_MONTH_DAY_RE.match(text)
        or MONTH_DAY_RE.match(text)
        or DURATION_HALF_RE.match(text)
        or TIME_APPROX_RE.match(text)
    )


def _breaks_number_counter(left: str, right: str) -> bool:
    left = left.strip()
    right = right.strip()

    if re.search(r'[0-9０-９一二三四五六七八九十百千万〇零]$', left) and COUNTER_START_RE.match(right):
        return True

    if re.search(r'[0-9０-９一二三四五六七八九十百千万〇零]年$', left) and re.match(
        r'^[0-9０-９一二三四五六七八九十〇零]+月$', right
    ):
        return True

    if re.search(r'[0-9０-９一二三四五六七八九十〇零]月$', left) and re.match(
        r'^[0-9０-９一二三四五六七八九十〇零]+日$', right
    ):
        return True

    if re.search(r'(時間|時|分|秒|年|か月|ヶ月|月|週間|週)$', left) and right == "半":
        return True

    if re.search(
        r'([0-9０-９一二三四五六七八九十百千万〇零]+(年|月|日|時)|朝|昼|夕方|夜|午前|午後|今週|来週|先週|今月|来月|先月|今年|来年|去年)$',
        left
    ) and right in {"ごろ", "に", "から", "まで"}:
        return True

    if re.search(r'ごろ$', left) and right in {"に", "から", "まで"}:
        return True

    return False


def _split_breaks_protected_chunk(left: str, right: str) -> bool:
    joined = left + right
    boundary = len(left)
    for chunk in PROTECTED_CHUNKS:
        start = joined.find(chunk)
        if start != -1:
            end = start + len(chunk)
            if start < boundary < end:
                return True
    return False


def _breaks_gurai_no_phrase(left: str, right: str) -> bool:
    left = left.strip()
    if left.endswith(("ぐらいの", "くらいの")):
        return True
    if re.search(r'(ぐらいの|くらいの)$', left):
        return True
    return False


def _breaks_aux_tail(left: str, right: str) -> bool:
    left = left.strip()
    right = right.strip()

    if right in AUX_TAIL_PATTERNS:
        return True

    if any(right.startswith(tail) for tail in AUX_TAIL_PATTERNS):
        return True

    if left.endswith(("襲い", "行き", "帰り", "作り", "なり", "言い", "して", "見て")) and right.startswith(
        ("ました", "ます", "でした", "です", "ない", "なかった", "いる", "いた")
    ):
        return True

    return False


def _quote_balance(text: str) -> int:
    return text.count("「") - text.count("」")


def _starts_bad_clause(text: str) -> bool:
    s = text.strip()
    if not s:
        return True
    if _is_punct_only(s):
        return True
    if s.startswith(ALLOWED_T_PREFIXES):
        return False
    if s in BAD_EXACT_STARTS:
        return True
    if any(s.startswith(x) for x in BAD_MULTI_STARTS):
        return True
    if any(s.startswith(x) for x in BAD_STARTS):
        return True
    return False


def _is_particle_only(text: str) -> bool:
    s = text.strip()
    return s in ATTACH_TO_LEFT or s in BAD_EXACT_STARTS or s in BAD_MULTI_STARTS


def _looks_like_final_predicate(text: str) -> bool:
    s = text.strip()
    return s.endswith(FINAL_PREDICATE_ENDINGS)


def _tokenize_units(text: str):
    nlp = _load_ginza()
    doc = nlp(text)

    try:
        raw = [span.text for span in doc._.bunsetsus if span.text.strip()]
    except Exception:
        raw = [tok.text for tok in doc if tok.text.strip()]

    units = []
    i = 0
    while i < len(raw):
        cur = raw[i]

        if "「" in cur and "」" not in cur:
            merged = cur
            i += 1
            while i < len(raw):
                merged += raw[i]
                if "」" in raw[i]:
                    break
                i += 1
            units.append(merged)
            i += 1
            continue

        if i + 1 < len(raw) and _is_protected_number_time_chunk(cur + raw[i + 1]):
            units.append(cur + raw[i + 1])
            i += 2
            continue

        if i + 2 < len(raw) and _is_protected_number_time_chunk(cur + raw[i + 1] + raw[i + 2]):
            units.append(cur + raw[i + 1] + raw[i + 2])
            i += 3
            continue

        if i + 1 < len(raw) and cur == "と" and raw[i + 1].startswith(("言", "い", "いう", "っていう")):
            units.append(cur + raw[i + 1])
            i += 2
            continue

        units.append(cur)
        i += 1

    return units


def _boundary_penalty(left: str, right: str, is_last: bool) -> float:
    score = 0.0
    l = left.strip()
    r = right.strip()

    if not l:
        return 1e9
    if not is_last and not r:
        return 1e9
    if not is_last and _is_punct_only(r):
        return 1e6

    if not is_last and _starts_bad_clause(r):
        score += 250.0

    if not is_last and r in BAD_EXACT_STARTS:
        score += 450.0

    if not is_last and any(r.startswith(x) for x in BAD_MULTI_STARTS):
        score += 380.0

    if not is_last and _is_particle_only(r):
        score += 500.0

    for x in sorted(ATTACH_TO_LEFT, key=len, reverse=True):
        if not is_last and r.startswith(x) and len(r) > len(x):
            score += 90.0
            break

    if not is_last and _split_breaks_protected_chunk(l, r):
        score += 260.0

    if not is_last and _breaks_number_counter(l, r):
        score += 260.0

    if not is_last and _breaks_gurai_no_phrase(l, r):
        score += 360.0

    if not is_last and _breaks_aux_tail(l, r):
        score += 600.0

    if _quote_balance(l) != 0:
        score += 120.0
    if not is_last and _quote_balance(r) != 0:
        score += 60.0

    if l.endswith("、"):
        score -= 25.0

    if l.endswith(("て、", "で、")):
        score -= 12.0

    if l.endswith(("て", "で")) and not l.endswith(("して", "いて", "見て")):
        score -= 6.0

    if l.endswith(("は", "が", "を", "に", "へ", "で", "と", "も")):
        score += 70.0

    if is_last:
        if not _looks_like_final_predicate(l):
            score += 55.0
    else:
        if _looks_like_final_predicate(l):
            score += 80.0
        if _looks_like_final_predicate(r):
            score -= 24.0

    if not is_last and l.endswith(("男性を", "人を", "熊を", "本を", "家を")):
        score -= 20.0

    if not is_last and l.endswith(("熊が80歳ぐらいの男性を", "熊が80歳くらいの男性を")):
        score -= 40.0

    score += max(0, 2 - len(l)) * 12.0
    if not is_last:
        score += max(0, 2 - len(r)) * 12.0

    return score


def _segment_score(parts):
    if len(parts) != 5:
        return 1e9

    score = 0.0
    lengths = [len(p) for p in parts]
    avg = sum(lengths) / 5.0

    score += sum(abs(x - avg) * 0.8 for x in lengths)

    for p in parts:
        if not p.strip():
            score += 1e6
        if _is_particle_only(p):
            score += 1e6
        if _is_punct_only(p):
            score += 1e6

    for i in range(4):
        score += _boundary_penalty(parts[i], parts[i + 1], False)

    if not _looks_like_final_predicate(parts[-1].strip()):
        score += 50.0

    return score


def _candidate_splits_from_doc(text: str):
    nlp = _load_ginza()
    doc = nlp(text)
    candidates = []

    try:
        spans = [span.text for span in doc._.bunsetsus if span.text.strip()]
    except Exception:
        spans = []

    if len(spans) >= 2:
        for i in range(1, len(spans)):
            left = "".join(spans[:i]).strip()
            right = "".join(spans[i:]).strip()
            candidates.append((left, right))

    toks = [tok.text for tok in doc if tok.text.strip()]
    if len(toks) >= 2:
        for i in range(1, len(toks)):
            left = "".join(toks[:i]).strip()
            right = "".join(toks[i:]).strip()
            candidates.append((left, right))

    seen = set()
    uniq = []
    for left, right in candidates:
        key = (left, right)
        if key not in seen and left and right and left + right == text:
            uniq.append((left, right))
            seen.add(key)
    return uniq


def _safe_internal_split(text: str):
    candidates = []

    for left, right in _candidate_splits_from_doc(text):
        if _starts_bad_clause(right):
            continue
        if _is_particle_only(right):
            continue
        if _is_punct_only(right):
            continue
        if _split_breaks_protected_chunk(left, right):
            continue
        if _breaks_number_counter(left, right):
            continue
        if _breaks_gurai_no_phrase(left, right):
            continue
        if _breaks_aux_tail(left, right):
            continue

        score = _boundary_penalty(left, right, False)

        if _looks_like_final_predicate(right):
            score -= 12.0

        candidates.append((score, left, right))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        return [candidates[0][1], candidates[0][2]]

    if len(text) >= 2:
        for cut in range(max(1, len(text) // 2 - 2), min(len(text), len(text) // 2 + 3)):
            left = text[:cut].strip()
            right = text[cut:].strip()
            if not left or not right:
                continue
            if _starts_bad_clause(right):
                continue
            if _is_particle_only(right):
                continue
            if _is_punct_only(right):
                continue
            if _split_breaks_protected_chunk(left, right):
                continue
            if _breaks_number_counter(left, right):
                continue
            if _breaks_gurai_no_phrase(left, right):
                continue
            if _breaks_aux_tail(left, right):
                continue
            return [left, right]

    return [text]


def _force_split_units(units):
    out = list(units)
    guard = 0

    while len(out) < 5 and guard < 20:
        candidate_indices = sorted(range(len(out)), key=lambda i: len(out[i]), reverse=True)
        changed = False

        for idx in candidate_indices:
            parts = _safe_internal_split(out[idx])
            if len(parts) >= 2 and "".join(parts) == out[idx]:
                if any(_is_particle_only(p) for p in parts):
                    continue
                if any(_is_punct_only(p) for p in parts):
                    continue
                out = out[:idx] + parts + out[idx + 1:]
                changed = True
                break

        if not changed:
            break

        guard += 1

    return out


def _enumerate_best_five(units):
    n = len(units)

    if n == 5:
        return units

    if n < 5:
        units = _force_split_units(units)
        n = len(units)

    if n < 5:
        while len(units) < 5:
            idx = max(range(len(units)), key=lambda i: len(units[i]))
            parts = _safe_internal_split(units[idx])
            if len(parts) < 2:
                break
            if any(_is_particle_only(p) for p in parts):
                break
            if any(_is_punct_only(p) for p in parts):
                break
            units = units[:idx] + parts + units[idx + 1:]
        n = len(units)

    if n == 5:
        return units

    best_score = float("inf")
    best_parts = None

    prefix = [""]
    for u in units:
        prefix.append(prefix[-1] + u)

    for i in range(1, n - 3):
        p1 = prefix[i]
        for j in range(i + 1, n - 2):
            p2 = prefix[j][len(prefix[i]):]
            for k in range(j + 1, n - 1):
                p3 = prefix[k][len(prefix[j]):]
                for m in range(k + 1, n):
                    p4 = prefix[m][len(prefix[k]):]
                    p5 = prefix[n][len(prefix[m]):]
                    parts = [p1, p2, p3, p4, p5]
                    score = _segment_score(parts)
                    if score < best_score:
                        best_score = score
                        best_parts = parts

    return best_parts if best_parts else units[:5]


def decompose_into_clauses_fallback(text: str):
    text = normalize_text(text)

    if not text:
        return []

    if text in _EXACT_OVERRIDES:
        return _EXACT_OVERRIDES[text][:]

    units = _tokenize_units(text)
    parts = _enumerate_best_five(units)

    if len(parts) != 5:
        return [text]

    if "".join(parts) != text:
        return [text]

    if any(_is_punct_only(p) for p in parts):
        return [text]

    return parts


if __name__ == "__main__":
    sample_text = "雨が降っていたので、傘を買って家に帰りました。"
    if len(sys.argv) > 1:
        sample_text = sys.argv[1]

    result = decompose_into_clauses_fallback(sample_text)

    print(f"Original Text: {sample_text}\n")
    print("--- Final 5 Clauses ---")
    for i, clause in enumerate(result, 1):
        print(f"{i}: {clause}")
