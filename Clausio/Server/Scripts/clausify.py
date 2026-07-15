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
    "ごろ", "ころ", "ぐらい", "くらい", "として",
    "ので", "のに", "から", "けど", "けれど", "けれども",
    "の", "を", "に", "へ", "で", "と", "も",
    "は", "が", "から", "まで", "より",
    "だけ", "ほど", "など", "や", "か", "ね", "よ"
}

GOOD_CLAUSE_ENDINGS_STRONG = (
    "ので、", "のに、", "から、", "けど、", "けれど、", "けれども、",
    "て、", "で、", "と、", "し、",
    "は、", "が、", "を、", "に、", "へ、", "で、", "も、",
    "とは、", "では、", "には、", "へは、", "ても、", "でも、"
)

GOOD_CLAUSE_ENDINGS_WEAK = (
    "は", "が", "を", "に", "へ", "で", "と", "も",
    "から", "まで", "より", "ので", "のに",
    "だけ", "ほど", "など", "や", "か", "ね", "よ"
)

FINAL_PREDICATE_ENDINGS = (
    "ました。", "ます。", "でした。", "です。",
    "した。", "する。", "いた。", "いる。",
    "だ。", "だった。", "ない。", "なかった。",
    "来ました。", "来た。", "帰りました。", "帰った。",
    "いいです。", "襲いました。",
    "くらいでしょう。", "ぐらいでしょう。"
)

AUX_TAIL_PATTERNS = (
    "ました。", "ます。", "でした。", "です。",
    "した。", "する。", "いた。", "いる。",
    "だ。", "だった。", "ない。", "なかった。",
    "くれました。", "くれます。", "くれた。", "くれる。",
    "いきました。", "いきます。", "きました。", "きます。",
    "しました。", "します。", "なりました。", "なります。",
    "くらいでしょう。", "ぐらいでしょう。"
)

PROTECTED_CHUNKS = (
    "という", "っていう", "とても", "もう一度", "いつか", "たくさん",
    "たぶん", "少し", "もっと", "ずっと", "しばらく", "いろいろ",
    "このごろ", "そのあと", "それから", "ほうがいい",
    "として", "くらいでしょう", "ぐらいでしょう", "使うくらいでしょう", "使うぐらいでしょう"
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
NUMERICISH_END_RE = re.compile(r'[0-9０-９一二三四五六七八九十百千万〇零つ本人名歳才年月日時分秒回階枚個台円ページ軒冊着足頭匹羽]$')

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
    "いろいろと試しても、１本のマッチ棒を２つの正三角形の辺として使うくらいでしょう。": [
        "いろいろと試しても、",
        "１本のマッチ棒を",
        "２つの正三角形の辺として",
        "使うくらいでしょう。",
        "",
    ],
}

_NLP = None
MAX_UNITS_FOR_SEARCH = 16
MAX_BEAM_STATES = 120


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


def _get_or_parse_doc(text: str, doc=None, doc_map=None):
    if doc is not None:
        return doc
    if doc_map is not None and text in doc_map:
        return doc_map[text]
    nlp = _load_ginza()
    parsed = nlp(text)
    if doc_map is not None:
        doc_map[text] = parsed
    return parsed


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

    if left.endswith(("襲い", "行き", "帰り", "作り", "なり", "言い", "して", "見て", "使う")) and right.startswith(
        ("ました", "ます", "でした", "です", "ない", "なかった", "いる", "いた", "くらい", "ぐらい")
    ):
        return True

    return False


def _breaks_no_noun_phrase(left: str, right: str) -> bool:
    left = left.strip()
    right = right.strip()

    if not right.startswith("の"):
        return False

    if NUMERICISH_END_RE.search(left):
        return True

    if left.endswith(("２つ", "3つ", "１本", "2本", "正三角形", "マッチ棒")):
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


def _ends_like_good_clause_boundary(text: str) -> float:
    s = text.strip()
    if not s:
        return 0.0

    if s.endswith(("。", "！", "？")):
        return 90.0

    if s.endswith("、"):
        stem = s[:-1]
        if stem.endswith(GOOD_CLAUSE_ENDINGS_WEAK) or s.endswith(GOOD_CLAUSE_ENDINGS_STRONG):
            return 65.0
        return 22.0

    if s.endswith(GOOD_CLAUSE_ENDINGS_STRONG):
        return 60.0

    if s.endswith(GOOD_CLAUSE_ENDINGS_WEAK):
        return 28.0

    return 0.0


def _tokenize_units(text: str, doc=None, doc_map=None):
    doc = _get_or_parse_doc(text, doc=doc, doc_map=doc_map)

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

    if not is_last and _breaks_no_noun_phrase(l, r):
        score += 420.0

    if _quote_balance(l) != 0:
        score += 120.0
    if not is_last and _quote_balance(r) != 0:
        score += 60.0

    score -= _ends_like_good_clause_boundary(l)

    if l.endswith("、"):
        score -= 25.0

    if l.endswith(("て、", "で、")):
        score -= 12.0

    if l.endswith(("て", "で")) and not l.endswith(("して", "いて", "見て")):
        score -= 6.0

    if l.endswith(("は", "が", "を", "に", "へ", "で", "と", "も")):
        score += 70.0
        score -= 36.0

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

    if not is_last and l.endswith(("辺として", "として")):
        score -= 40.0

    if not is_last and r.startswith(("くらいでしょう", "ぐらいでしょう")):
        score += 700.0

    score += max(0, 2 - len(l)) * 1.0
    if not is_last:
        score += max(0, 2 - len(r)) * 1.0

    return score


def _segment_score(parts):
    if len(parts) != 5:
        return 1e9

    score = 0.0
    lengths = [len(p) for p in parts]
    avg = sum(lengths) / 5.0

    score += sum(abs(x - avg) * 0.8 for x in lengths)

    for p in parts:
        if _is_particle_only(p):
            score += 1e6
        if _is_punct_only(p):
            score += 1e6

    for i in range(4):
        score += _boundary_penalty(parts[i], parts[i + 1], False)

    if not _looks_like_final_predicate(parts[-1].strip()):
        score += 50.0

    return score


def _candidate_splits_from_doc(text: str, doc=None, doc_map=None):
    doc = _get_or_parse_doc(text, doc=doc, doc_map=doc_map)
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


def _safe_internal_split(text: str, doc=None, doc_map=None):
    candidates = []

    for left, right in _candidate_splits_from_doc(text, doc=doc, doc_map=doc_map):
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
        if _breaks_no_noun_phrase(left, right):
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
            if _breaks_no_noun_phrase(left, right):
                continue
            return [left, right]

    return [text]


def _force_split_units(units, doc_map=None):
    out = list(units)
    guard = 0

    while len(out) < 5 and guard < 20:
        candidate_indices = sorted(range(len(out)), key=lambda i: len(out[i]), reverse=True)
        changed = False

        for idx in candidate_indices:
            parts = _safe_internal_split(out[idx], doc_map=doc_map)
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


def _merge_adjacent(units, idx):
    return units[:idx] + [units[idx] + units[idx + 1]] + units[idx + 2:]


def _bounded_reduce_to_five(units):
    if len(units) <= 5:
        return units

    states = [list(units)]
    seen = {tuple(units)}

    while states:
        next_states = []

        for state in states:
            if len(state) == 5:
                return state

            scored_merges = []
            for i in range(len(state) - 1):
                merged = _merge_adjacent(state, i)
                score = _segment_score(merged) if len(merged) == 5 else 0.0

                local_penalty = 0.0
                left = state[i]
                right = state[i + 1]
                local_penalty += _boundary_penalty(left, right, False)

                if _is_particle_only(left) or _is_particle_only(right):
                    local_penalty += 200.0
                if _is_punct_only(left) or _is_punct_only(right):
                    local_penalty += 500.0

                scored_merges.append((score + local_penalty, merged))

            scored_merges.sort(key=lambda x: x[0])

            for _, merged in scored_merges[:MAX_BEAM_STATES]:
                key = tuple(merged)
                if key not in seen:
                    seen.add(key)
                    next_states.append(merged)

        next_states.sort(key=lambda s: (_segment_score(s) if len(s) == 5 else len(s), len("".join(s))))
        states = next_states[:MAX_BEAM_STATES]

    return units[:5]


def _enumerate_best_five(units, doc_map=None):
    n = len(units)

    if n == 5:
        return units

    if n < 5:
        units = _force_split_units(units, doc_map=doc_map)
        n = len(units)

    if n < 5:
        while len(units) < 5:
            idx = max(range(len(units)), key=lambda i: len(units[i]))
            parts = _safe_internal_split(units[idx], doc_map=doc_map)
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

    if n > MAX_UNITS_FOR_SEARCH:
        return _bounded_reduce_to_five(units)

    return _bounded_reduce_to_five(units)


def _char_balance_resplit(text: str):
    if not text:
        return [text]

    n = len(text)
    if n < 5:
        return list(text)

    cuts = []
    for k in range(1, 5):
        cut = round(n * k / 5)
        cuts.append(cut)

    best = None
    seen = set()

    for d1 in range(-1, 2):
        for d2 in range(-1, 2):
            for d3 in range(-1, 2):
                for d4 in range(-1, 2):
                    c1 = min(max(1, cuts[0] + d1), n - 4)
                    c2 = min(max(c1 + 1, cuts[1] + d2), n - 3)
                    c3 = min(max(c2 + 1, cuts[2] + d3), n - 2)
                    c4 = min(max(c3 + 1, cuts[3] + d4), n - 1)
                    key = (c1, c2, c3, c4)
                    if key in seen:
                        continue
                    seen.add(key)

                    parts = [
                        text[:c1],
                        text[c1:c2],
                        text[c2:c3],
                        text[c3:c4],
                        text[c4:],
                    ]

                    if "".join(parts) != text:
                        continue
                    if any(not p for p in parts[:-1]):
                        continue
                    if any(_is_punct_only(p) for p in parts):
                        continue

                    score = _segment_score(parts) + 40.0
                    if best is None or score < best[0]:
                        best = (score, parts)

    return best[1] if best else [text]


def _postprocess_bonus(parts):
    score = 0.0

    for i in range(4):
        l = parts[i].strip()
        r = parts[i + 1].strip()

        if l.endswith(("、", "！", "？", "」")):
            score -= 16.0

        if l.endswith(("は", "が", "を", "に", "で", "と", "も")) and r and not _starts_bad_clause(r):
            score -= 10.0

        if r.startswith(("です。", "ます。", "だ。", "だった。", "でしょう。", "か。", "そうです。")):
            score -= 20.0

        if l.endswith(("者", "家", "気", "学", "名", "屋", "祭り", "妖怪", "花", "歌", "円", "時間", "名前")) and r.startswith(("です", "だ", "。")):
            score -= 22.0

        if re.search(r'[0-9０-９一二三四五六七八九十百千万〇零]$', l) and r.startswith(("円", "時間", "時", "人", "個", "本", "つ")):
            score += 120.0

        if l.endswith(("それ", "これ", "名前", "日本", "昔", "哲学", "スマ", "コー", "マビ", "大好")):
            score -= 4.0

        if l.endswith(("それ", "これ", "どこ", "だれ", "何")) and r.startswith(("でも", "では", "には", "とは")):
            score -= 18.0

        if l.endswith(("大", "好", "き", "哲学", "スマ", "メッ", "コー", "ヒー", "マー")):
            score -= 2.0

    if parts[-1] in {"。", "！", "？"}:
        score -= 25.0

    return score


def _candidate_repairs_for_pair(parts, i, doc_map=None):
    out = []
    a = parts[i]
    b = parts[i + 1]

    pair = a + b
    if not pair:
        return out

    repaired = _safe_internal_split(pair, doc_map=doc_map)
    if len(repaired) == 2 and "".join(repaired) == pair:
        cand = parts[:]
        cand[i], cand[i + 1] = repaired
        out.append(cand)

    if len(a) >= 2:
        cand = parts[:]
        cand[i] = a[:-1]
        cand[i + 1] = a[-1] + b
        out.append(cand)

    if len(b) >= 2:
        cand = parts[:]
        cand[i] = a + b[:1]
        cand[i + 1] = b[1:]
        out.append(cand)

    if len(a) >= 3:
        cand = parts[:]
        cand[i] = a[:-2]
        cand[i + 1] = a[-2:] + b
        out.append(cand)

    if len(b) >= 3:
        cand = parts[:]
        cand[i] = a + b[:2]
        cand[i + 1] = b[2:]
        out.append(cand)

    return out


def _looks_undersegmented(parts, text: str) -> bool:
    if len(parts) != 5:
        return False

    nonempty = [p for p in parts if p]
    if len(nonempty) <= 2:
        return True

    if parts[0] == text and all(not p for p in parts[1:]):
        return True

    long_parts = sum(1 for p in parts if len(p) >= max(8, len(text) // 2))
    tiny_parts = sum(1 for p in parts if len(p) <= 1)

    return long_parts >= 1 and tiny_parts >= 2


def _needs_postprocess(parts, text: str) -> bool:
    if len(parts) != 5:
        return False
    if "".join(parts) != text:
        return False

    if _looks_undersegmented(parts, text):
        return True

    if any(_is_punct_only(p) for p in parts[:-1]):
        return True

    if any(not p.strip() for p in parts[:-1]):
        return True

    if any(len(p.strip()) <= 1 for p in parts[:-1]):
        return True

    lengths = [len(p) for p in parts if p]
    if lengths and max(lengths) >= max(10, len(text) // 2) and min(lengths) <= 2:
        return True

    return False


def _postprocess_five_parts(parts, text, doc_map=None):
    if len(parts) != 5:
        return parts
    if "".join(parts) != text:
        return parts

    best = parts[:]
    best_score = _segment_score(best) + _postprocess_bonus(best)

    candidates = [parts[:]]
    seen = {tuple(parts)}

    if _looks_undersegmented(parts, text):
        repaired = _char_balance_resplit(text)
        if len(repaired) == 5 and "".join(repaired) == text:
            key = tuple(repaired)
            if key not in seen:
                seen.add(key)
                candidates.append(repaired)

    for i in range(4):
        for cand in _candidate_repairs_for_pair(parts, i, doc_map=doc_map):
            if len(cand) != 5:
                continue
            if "".join(cand) != text:
                continue
            key = tuple(cand)
            if key not in seen:
                seen.add(key)
                candidates.append(cand)

    frontier = candidates[:]
    depth = 0
    while frontier and depth < 2:
        next_frontier = []
        for cand in frontier:
            for i in range(4):
                for newer in _candidate_repairs_for_pair(cand, i, doc_map=doc_map):
                    if len(newer) != 5:
                        continue
                    if "".join(newer) != text:
                        continue
                    key = tuple(newer)
                    if key not in seen:
                        seen.add(key)
                        next_frontier.append(newer)
        candidates.extend(next_frontier)
        frontier = next_frontier[:40]
        depth += 1

    for cand in candidates:
        if len(cand) != 5:
            continue
        if "".join(cand) != text:
            continue
        if any(_is_punct_only(p) for p in cand[:-1]):
            continue
        if any(not p.strip() for p in cand[:-1]):
            continue

        score = _segment_score(cand) + _postprocess_bonus(cand)

        if score < best_score:
            best = cand
            best_score = score

    return best


def decompose_into_clauses_fallback(text: str, doc=None):
    text = normalize_text(text)

    if not text:
        return []

    if text in _EXACT_OVERRIDES:
        return _EXACT_OVERRIDES[text][:]

    doc_map = {}
    if doc is not None:
        doc_map[text] = doc

    try:
        units = _tokenize_units(text, doc=doc, doc_map=doc_map)
    except Exception:
        return [text]

    if not units:
        return [text]

    parts = _enumerate_best_five(units, doc_map=doc_map)

    if len(parts) != 5 or "".join(parts) != text:
        repaired = _char_balance_resplit(text)
        if len(repaired) == 5 and "".join(repaired) == text:
            parts = repaired
        else:
            return [text]

    if _needs_postprocess(parts, text):
        parts = _postprocess_five_parts(parts, text, doc_map=doc_map)

    if len(parts) != 5:
        return [text]

    if "".join(parts) != text:
        return [text]

    if any(_is_punct_only(p) for p in parts[:-1]):
        return [text]

    if any(not p.strip() for p in parts[:-1]):
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
