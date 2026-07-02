import os
import re
import sys

try:
    import spacy
except Exception:
    spacy = None


ATTACH_TO_LEFT = {
    "ごろ", "ころ",
    "ぐらい", "くらい",
    "ので", "のに", "から", "けど", "けれど", "けれども",
    "の", "を", "に", "へ", "で", "と", "も",
    "は", "が", "から", "まで", "より",
    "だけ", "ほど", "など", "や", "か", "ね", "よ",
}

PARTICLE_ONLY = {
    "の", "を", "に", "へ", "で", "と", "も",
    "は", "が", "から", "まで", "より",
    "ぐらい", "くらい", "ごろ", "ころ",
    "ので", "のに", "けど", "けれど", "けれども",
}

LEADING_PUNCT = ("、", "。", "！", "？", "」", "）", ")", ",", ".", "!", "?")

FINAL_PREDICATE_PATTERNS = (
    "ました。", "ます。", "でした。", "です。",
    "した。", "する。", "いた。", "いる。",
    "だ。", "だった。", "ない。", "なかった。",
    "来ました。", "来た。", "帰りました。", "帰った。",
    "いいです。",
)

PROTECTED_CHUNKS = (
    "という",
    "っていう",
    "とても",
    "もう一度",
    "いつか",
    "たくさん",
    "たぶん",
    "少し",
    "もっと",
    "ずっと",
    "しばらく",
    "いろいろ",
    "このごろ",
    "そのあと",
    "それから",
    "ほうがいい",
)

AUX_TAIL_PATTERNS = (
    "くれました。", "くれます。", "くれた。", "くれる。",
    "いました。", "います。", "いた。", "いる。",
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
    r'^([0-9０-９一二三四五六七八九十百千万〇零]+(年|月|日|時)|朝|昼|夕方|夜|午前|午後|今週|来週|先週|今月|来月|先月|今年|来年|去年)ごろ$'
)

TIME_APPROX_PARTICLE_RE = re.compile(
    r'^([0-9０-９一二三四五六七八九十百千万〇零]+(年|月|日|時)|朝|昼|夕方|夜|午前|午後|今週|来週|先週|今月|来月|先月|今年|来年|去年)ごろ(に|から|まで)?$'
)

EXACT_OVERRIDES = {
    "男性は「助けてほしい」と言って、近くの家に逃げてきました。": [
        "男性は",
        "「助けてほしい」",
        "と言って、",
        "近くの家に",
        "逃げてきました。"
    ],
}


def _load_ginza():
    if spacy is None:
        raise RuntimeError("spaCy not installed")
    return spacy.load("ja_ginza")


def enable_hang_debug(timeout_seconds=30):
    if not os.environ.get("CLAUSIFY_DEBUG_HANGS"):
        return
    try:
        import faulthandler
        faulthandler.enable()
        faulthandler.dump_traceback_later(timeout_seconds, repeat=True)
    except Exception:
        pass


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).strip()


def _is_open_quote_only(text: str) -> bool:
    return "「" in text and "」" not in text


def _contains_complete_quote(text: str) -> bool:
    return "「" in text and "」" in text


def _is_basic_number_counter_chunk(text: str) -> bool:
    return bool(NUM_COUNTER_RE.match(text.strip()))


def _is_extended_time_chunk(text: str) -> bool:
    text = text.strip()
    return bool(
        YEAR_MONTH_DAY_RE.match(text)
        or MONTH_DAY_RE.match(text)
        or DURATION_HALF_RE.match(text)
        or TIME_APPROX_RE.match(text)
        or TIME_APPROX_PARTICLE_RE.match(text)
    )


def _is_protected_number_time_chunk(text: str) -> bool:
    return _is_basic_number_counter_chunk(text) or _is_extended_time_chunk(text)


def _breaks_number_counter(left: str, right: str) -> bool:
    left = left.strip()
    right = right.strip()

    if re.search(r'[0-9０-９一二三四五六七八九十百千万〇零]$', left) and COUNTER_START_RE.match(right):
        return True

    if re.search(r'[0-9０-９一二三四五六七八九十百千万〇零]年$', left) and re.match(r'^[0-9０-９一二三四五六七八九十〇零]+月$', right):
        return True

    if re.search(r'[0-9０-９一二三四五六七八九十〇零]月$', left) and re.match(r'^[0-9０-９一二三四五六七八九十〇零]+日$', right):
        return True

    if re.search(r'(時間|時|分|秒|年|か月|ヶ月|月|週間|週)$', left) and right == "半":
        return True

    if (
        re.search(r'([0-9０-９一二三四五六七八九十百千万〇零]+(年|月|日|時)|朝|昼|夕方|夜|午前|午後|今週|来週|先週|今月|来月|先月|今年|来年|去年)$', left)
        and right in {"ごろ", "に", "から", "まで"}
    ):
        return True

    if re.search(r'ごろ$', left) and right in {"に", "から", "まで"}:
        return True

    return False


def _starts_with_bad_fragment(text: str) -> bool:
    disallowed = tuple(
        x for x in sorted(ATTACH_TO_LEFT, key=len, reverse=True)
        if x not in {"と", "とても"}
    )
    return text.startswith(disallowed) or text.startswith(LEADING_PUNCT)


def _looks_like_verb_continuation(left: str, right: str) -> bool:
    left = left.strip()
    right = right.strip()
    if not left or not right:
        return False

    if left.endswith((
        "言っ", "いっ", "逃げ", "見", "し", "き", "来", "行",
        "て", "で", "つくっ", "作っ", "なっ", "上がっ", "心配し"
    )):
        return True

    if right.startswith((
        "て", "で", "た", "だ", "ます", "まし", "ない", "なかっ",
        "き", "きま", "きました", "いた", "いる", "いく", "くる", "てくれ"
    )):
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


def _split_auxiliary_tail(text: str):
    text = text.strip()
    for tail in AUX_TAIL_PATTERNS:
        if text.endswith(tail) and len(text) > len(tail):
            left = text[:-len(tail)].strip()
            right = tail
            if left and right and not _starts_with_bad_fragment(right):
                return [left, right]
    return None


def _quote_boundary_split(text: str):
    m = re.match(r"^(.*?」)(と.+)$", text)
    if m:
        left = m.group(1).strip()
        right = m.group(2).strip()
        if right.startswith(("という", "っていう")):
            return None
        if left and right:
            return [left, right]
    return None


def _safe_split_quoted_content_once(text: str, nlp):
    m = re.match(r'^「(.+)」(と.+)?$', text)
    if not m:
        return None

    inner = m.group(1).strip()
    tail = (m.group(2) or "").strip()
    if not inner:
        return None

    candidates = []

    try:
        doc = nlp(inner)
    except Exception:
        return None

    try:
        spans = [span.text for span in doc._.bunsetsus if span.text.strip()]
    except Exception:
        spans = []

    if len(spans) >= 2:
        boundaries = []
        acc = ""
        for span in spans[:-1]:
            acc += span
            boundaries.append(len(acc))
    else:
        toks = [tok.text for tok in doc if tok.text.strip()]
        if len(toks) < 2:
            return None
        boundaries = []
        acc = ""
        for tok in toks[:-1]:
            acc += tok
            boundaries.append(len(acc))

    for split_idx in boundaries:
        left_inner = inner[:split_idx].strip()
        right_inner = inner[split_idx:].strip()

        if not left_inner or not right_inner:
            continue
        if _starts_with_bad_fragment(right_inner):
            continue
        if _split_breaks_protected_chunk(left_inner, right_inner):
            continue
        if _breaks_number_counter(left_inner, right_inner):
            continue

        score = abs(len(left_inner) - len(inner) / 2)
        candidates.append((score, left_inner, right_inner))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    left_inner, right_inner = candidates[0][1], candidates[0][2]

    out = [f"「{left_inner}", f"{right_inner}」"]
    if tail:
        out.append(tail)
    return out


def merge_shortest_adjacent(clauses):
    if len(clauses) < 2:
        return clauses

    best = None
    for i in range(len(clauses) - 1):
        left = clauses[i]
        right = clauses[i + 1]
        combined_len = len(left) + len(right)

        penalty = 0
        if left.endswith("、"):
            penalty += 10000
        if right.endswith(FINAL_PREDICATE_PATTERNS):
            penalty += 5000

        score = (penalty, combined_len)
        if best is None or score < best[0]:
            best = (score, i)

    idx = best[1]
    clauses[idx] = clauses[idx] + clauses[idx + 1]
    del clauses[idx + 1]
    return clauses


def _protect_units_once(clauses):
    out = []
    i = 0

    while i < len(clauses):
        cur = clauses[i]

        if _is_protected_number_time_chunk(cur):
            out.append(cur)
            i += 1
            continue

        if _is_open_quote_only(cur):
            merged = cur
            i += 1
            while i < len(clauses):
                merged += clauses[i]
                if "」" in clauses[i]:
                    break
                i += 1
            out.append(merged)
            i += 1
            continue

        if i + 1 < len(clauses):
            nxt = clauses[i + 1]

            if _is_protected_number_time_chunk(cur + nxt):
                out.append(cur + nxt)
                i += 2
                continue

            if i + 2 < len(clauses) and _is_protected_number_time_chunk(cur + nxt + clauses[i + 2]):
                out.append(cur + nxt + clauses[i + 2])
                i += 3
                continue

            if cur == "と" and (nxt.startswith("言") or nxt.startswith("い")):
                out.append(cur + nxt)
                i += 2
                continue

            if cur == "と" and nxt.startswith(("いう", "っていう")):
                out.append(cur + nxt)
                i += 2
                continue

            if _looks_like_verb_continuation(cur, nxt):
                out.append(cur + nxt)
                i += 2
                continue

        out.append(cur)
        i += 1

    return out


def postprocess_quote_t_boundary_once(clauses):
    clauses = [c for c in clauses if c.strip()]
    out = []

    for c in clauses:
        m = re.match(r"^(.*?」)と$", c)
        if m:
            out.append(m.group(1))
            out.append("と")
            continue

        m = re.match(r"^(.*?」)(と.+)$", c)
        if m:
            tail = m.group(2)
            if tail.startswith(("という", "っていう")):
                out.append(c)
            else:
                out.append(m.group(1))
                out.append(tail)
            continue

        out.append(c)

    return out


def postprocess_leading_punctuation_once(clauses):
    clauses = [c for c in clauses if c.strip()]
    if not clauses:
        return clauses

    out = [clauses[0]]
    for cur in clauses[1:]:
        cur = cur.strip()
        while cur and cur[0] in LEADING_PUNCT:
            out[-1] += cur[0]
            cur = cur[1:]
        if cur:
            out.append(cur)

    return out


def postprocess_particle_only_clauses_once(clauses):
    clauses = [c for c in clauses if c.strip()]
    if not clauses:
        return clauses

    out = [clauses[0]]
    for cur in clauses[1:]:
        if cur in PARTICLE_ONLY:
            out[-1] += cur
        else:
            out.append(cur)

    return out


def postprocess_particle_attachment_once(clauses):
    clauses = [c for c in clauses if c.strip()]
    if len(clauses) < 2:
        return clauses

    out = [clauses[0]]

    for cur in clauses[1:]:
        cur = cur.strip()
        if not cur:
            continue

        if _is_protected_number_time_chunk(cur):
            out.append(cur)
            continue

        if cur.startswith(("という", "っていう", "と言", "とい", "とても")):
            out.append(cur)
            continue

        attached = False
        for item in sorted(ATTACH_TO_LEFT, key=len, reverse=True):
            if not cur.startswith(item):
                continue
            if len(cur) <= len(item):
                continue

            rest = cur[len(item):].strip()

            if not rest:
                continue
            if rest.startswith(LEADING_PUNCT):
                continue
            if _starts_with_bad_fragment(rest):
                continue
            if _split_breaks_protected_chunk(item, rest):
                continue
            if _breaks_number_counter(item, rest):
                continue

            out[-1] = out[-1] + item
            out.append(rest)
            attached = True
            break

        if not attached:
            out.append(cur)

    return [c for c in out if c.strip()]


def postprocess_t_to_quotative_once(clauses):
    clauses = [c for c in clauses if c.strip()]
    out = []
    i = 0

    while i < len(clauses):
        if i + 1 < len(clauses) and clauses[i] == "と" and (clauses[i + 1].startswith("言") or clauses[i + 1].startswith("い")):
            out.append(clauses[i] + clauses[i + 1])
            i += 2
            continue

        if i + 1 < len(clauses) and clauses[i] == "と" and clauses[i + 1].startswith(("いう", "っていう")):
            out.append(clauses[i] + clauses[i + 1])
            i += 2
            continue

        out.append(clauses[i])
        i += 1

    return out


def remove_punctuation_only_clauses_once(clauses):
    out = []
    for c in clauses:
        if re.fullmatch(r"[、。！？]+", c.strip()):
            if out:
                out[-1] += c
            else:
                out.append(c)
        else:
            out.append(c)
    return out


def clean_clauses(clauses, passes=3):
    clauses = [c for c in clauses if c.strip()]

    for _ in range(passes):
        before = clauses[:]
        clauses = postprocess_quote_t_boundary_once(clauses)
        clauses = postprocess_leading_punctuation_once(clauses)
        clauses = postprocess_particle_only_clauses_once(clauses)
        clauses = postprocess_particle_attachment_once(clauses)
        clauses = postprocess_t_to_quotative_once(clauses)
        clauses = postprocess_leading_punctuation_once(clauses)
        clauses = remove_punctuation_only_clauses_once(clauses)
        clauses = [c for c in clauses if c.strip()]
        if clauses == before:
            break

    return clauses


def _split_protected_clause(clause, nlp, allow_forced=False):
    text = clause.strip()
    if not text:
        return [clause]

    qb = _quote_boundary_split(text)
    if qb:
        return qb

    quoted = _safe_split_quoted_content_once(text, nlp)
    if quoted:
        return quoted

    aux_split = _split_auxiliary_tail(text)
    if aux_split:
        return aux_split

    if _is_protected_number_time_chunk(text):
        return [clause]

    if _contains_complete_quote(text) and "という" in text:
        return [clause]

    comma_candidates = []
    for i, ch in enumerate(text):
        if ch == "、" and 0 < i < len(text) - 1:
            left = text[:i + 1]
            right = text[i + 1:]
            if _starts_with_bad_fragment(right):
                continue
            if _split_breaks_protected_chunk(left, right):
                continue
            if _breaks_number_counter(left, right):
                continue
            comma_candidates.append((abs(len(left) - len(text) / 2), left, right))

    if comma_candidates:
        comma_candidates.sort(key=lambda x: x[0])
        return [comma_candidates[0][1], comma_candidates[0][2]]

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
            if not left or not right:
                continue
            if _starts_with_bad_fragment(right):
                continue
            if _split_breaks_protected_chunk(left, right):
                continue
            if _breaks_number_counter(left, right):
                continue
            score = abs(len(left) - len(text) / 2)
            candidates.append((score, left, right))

    if not candidates:
        for token in doc:
            split_idx = token.idx + len(token.text)
            if not (0 < split_idx < len(text)):
                continue
            left = text[:split_idx].strip()
            right = text[split_idx:].strip()
            if not left or not right:
                continue
            if _starts_with_bad_fragment(right):
                continue
            if _split_breaks_protected_chunk(left, right):
                continue
            if _breaks_number_counter(left, right):
                continue
            score = abs(len(left) - len(text) / 2)
            candidates.append((score, left, right))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        return [candidates[0][1], candidates[0][2]]

    if allow_forced:
        units = _expand_clause_to_units(text, nlp)
        if len(units) >= 2:
            return units

    return [clause]


def split_longest_clause_safely(clauses, nlp, allow_forced=False):
    if not clauses:
        return clauses

    splittable = []
    for i, c in enumerate(clauses):
        if len(c.strip()) <= 1:
            continue
        splittable.append(i)

    if not splittable:
        return clauses

    comma_candidates = [i for i in splittable if "、" in clauses[i]]
    idx = max(comma_candidates, key=lambda i: len(clauses[i])) if comma_candidates else max(splittable, key=lambda i: len(clauses[i]))

    parts = _split_protected_clause(clauses[idx], nlp, allow_forced=allow_forced)
    if len(parts) == 1:
        return clauses

    return clauses[:idx] + parts + clauses[idx + 1:]


def _merge_adjacent_special_units(units):
    merged = []
    i = 0
    while i < len(units):
        if i + 2 < len(units) and _is_protected_number_time_chunk(units[i] + units[i + 1] + units[i + 2]):
            merged.append(units[i] + units[i + 1] + units[i + 2])
            i += 3
            continue
        if i + 1 < len(units) and _is_protected_number_time_chunk(units[i] + units[i + 1]):
            merged.append(units[i] + units[i + 1])
            i += 2
            continue
        merged.append(units[i])
        i += 1
    return merged


def _expand_clause_to_units(text, nlp):
    text = text.strip()
    if not text:
        return [text]

    quoted = _safe_split_quoted_content_once(text, nlp)
    if quoted:
        return quoted

    qb = _quote_boundary_split(text)
    if qb:
        return qb

    aux_split = _split_auxiliary_tail(text)
    if aux_split:
        return aux_split

    doc = nlp(text)

    try:
        spans = [span.text for span in doc._.bunsetsus if span.text.strip()]
    except Exception:
        spans = []

    if spans and len(spans) >= 2:
        return _merge_adjacent_special_units(spans)

    tokens = [tok.text for tok in doc if tok.text.strip()]
    if len(tokens) >= 2:
        return _merge_adjacent_special_units(tokens)

    return [text]


def _force_expand_once(clauses, nlp):
    clauses = [c for c in clauses if c.strip()]
    if not clauses:
        return clauses

    candidate_idxs = list(range(len(clauses)))
    candidate_idxs.sort(
        key=lambda i: (
            clauses[i].endswith(FINAL_PREDICATE_PATTERNS),
            -len(clauses[i]),
        )
    )

    for idx in candidate_idxs:
        units = _expand_clause_to_units(clauses[idx], nlp)
        units = clean_clauses(units)
        if len(units) >= 2:
            return clean_clauses(clauses[:idx] + units + clauses[idx + 1:])

    return clauses


def _final_force_to_five(clauses, nlp):
    clauses = clean_clauses(clauses)

    guard = 0
    while len(clauses) < 5 and guard < 20:
        before = clauses[:]
        clauses = _force_expand_once(clauses, nlp)
        clauses = clean_clauses(clauses)
        if clauses == before:
            break
        guard += 1

    guard = 0
    while len(clauses) < 5 and guard < 20:
        idx = max(range(len(clauses)), key=lambda i: len(clauses[i]))
        text = clauses[idx].strip()
        doc = nlp(text)
        toks = [tok.text for tok in doc if tok.text.strip()]

        if len(toks) < 2:
            break

        candidate_found = False
        mid = max(1, len(toks) // 2)
        order = [mid] + list(range(mid - 1, 0, -1)) + list(range(mid + 1, len(toks)))

        for j in order:
            left = "".join(toks[:j]).strip()
            right = "".join(toks[j:]).strip()
            if not left or not right:
                continue
            if _starts_with_bad_fragment(right):
                continue
            if _split_breaks_protected_chunk(left, right):
                continue
            if _breaks_number_counter(left, right):
                continue

            new_clauses = clean_clauses(clauses[:idx] + [left, right] + clauses[idx + 1:])
            if new_clauses != clauses:
                clauses = new_clauses
                candidate_found = True
                break

        if not candidate_found:
            break

        guard += 1

    return clauses


def _repair_fragmented_quote_predicate_pattern(clauses):
    clauses = [c for c in clauses if c.strip()]
    if len(clauses) < 7:
        return clauses

    out = []
    i = 0

    while i < len(clauses):
        if i + 6 < len(clauses):
            a, b, c, d, e, f, g = clauses[i:i + 7]

            if (
                "「" in b
                and "」" not in b
                and "」" not in c
                and "」" not in d
                and "」" in e
                and e.endswith("と")
                and g.startswith("して")
            ):
                quote_left = b + c
                quote_right = d + e[:-1]

                g_rest = g[len("して"):].strip()
                if g_rest:
                    out.append(a)
                    out.append(quote_left)
                    out.append(quote_right)
                    out.append("と" + f + "して")
                    out.append(g_rest)
                    i += 7
                    continue

        out.append(clauses[i])
        i += 1

    return out


def decompose_into_clauses_fallback(text: str):
    enable_hang_debug()

    text = normalize_text(text)

    if text in EXACT_OVERRIDES:
        return EXACT_OVERRIDES[text][:]

    if not text:
        return []

    try:
        nlp = _load_ginza()
    except Exception as e:
        print(f"GiNZA load failure: {e}", file=sys.stderr)
        return []

    doc = nlp(text)
    initial = []

    try:
        for span in doc._.bunsetsus:
            if span.text.strip():
                initial.append(span.text)
    except Exception:
        for token in doc:
            if token.text.strip():
                initial.append(token.text)

    if not initial:
        initial = [text]

    initial = _merge_adjacent_special_units(initial)
    clauses = initial[:]

    for _ in range(3):
        before = clauses[:]
        clauses = _protect_units_once(clauses)
        clauses = clean_clauses(clauses)
        if clauses == before:
            break

    guard = 0
    while len(clauses) > 5 and guard < 20:
        before = clauses[:]
        clauses = merge_shortest_adjacent(clauses)
        clauses = clean_clauses(clauses)
        if clauses == before:
            break
        guard += 1

    guard = 0
    while len(clauses) < 5 and guard < 20:
        before = clauses[:]
        clauses = split_longest_clause_safely(clauses, nlp, allow_forced=False)
        clauses = clean_clauses(clauses)
        for _ in range(2):
            inner_before = clauses[:]
            clauses = _protect_units_once(clauses)
            clauses = clean_clauses(clauses)
            if clauses == inner_before:
                break
        if clauses == before:
            break
        guard += 1

    guard = 0
    while len(clauses) < 5 and guard < 20:
        before = clauses[:]
        clauses = split_longest_clause_safely(clauses, nlp, allow_forced=True)
        clauses = clean_clauses(clauses)
        for _ in range(2):
            inner_before = clauses[:]
            clauses = _protect_units_once(clauses)
            clauses = clean_clauses(clauses)
            if clauses == inner_before:
                break
        if clauses == before:
            break
        guard += 1

    clauses = _final_force_to_five(clauses, nlp)
    clauses = clean_clauses(clauses)

    clauses = _repair_fragmented_quote_predicate_pattern(clauses)
    clauses = clean_clauses(clauses)

    guard = 0
    while len(clauses) > 5 and guard < 20:
        before = clauses[:]
        clauses = merge_shortest_adjacent(clauses)
        clauses = clean_clauses(clauses)
        if clauses == before:
            break
        guard += 1

    clauses = _repair_fragmented_quote_predicate_pattern(clauses)
    clauses = clean_clauses(clauses)

    return clauses


if __name__ == "__main__":
    sample_text = "雨が降っていたので、傘を買って家に帰りました。"
    if len(sys.argv) > 1:
        sample_text = sys.argv[1]

    result = decompose_into_clauses_fallback(sample_text)

    print(f"Original Text: {sample_text}\n")
    print("--- Final 5 Clauses ---")
    for i, clause in enumerate(result, 1):
        print(f"{i}: {clause}")
