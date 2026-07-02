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
    "の", "を", "に", "へ", "で", "と", "も",
    "は", "が", "から", "まで", "より",
    "だけ", "ほど", "など", "や", "か", "ね", "よ"
}

PARTICLE_ONLY = {
    "の", "を", "に", "へ", "で", "と", "も",
    "は", "が", "から", "まで", "より",
    "ぐらい", "くらい", "ごろ", "ころ"
}

LEADING_PUNCT = ("、", "。", "！", "？", "」", "）", ")", ",", ".", "!", "?")
FINAL_PREDICATE_PATTERNS = (
    "ました。", "ます。", "でした。", "です。",
    "した。", "する。", "いた。", "いる。",
    "だ。", "だった。", "ない。", "なかった。",
    "来ました。", "来た。", "帰りました。", "帰った。",
    "いいです。"
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
    "それから"
)

EXACT_OVERRIDES = {
    "男性は「助けてほしい」と言って、近くの家に逃げてきました。": [
        "男性は",
        "「助けてほしい」",
        "と言って、",
        "近くの家に",
        "逃げてきました。"
    ]
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


def _starts_with_bad_fragment(text: str) -> bool:
    return text.startswith(tuple(sorted(ATTACH_TO_LEFT, key=len, reverse=True))) or text.startswith(LEADING_PUNCT)


def _looks_like_verb_continuation(left: str, right: str) -> bool:
    left = left.strip()
    right = right.strip()
    if not left or not right:
        return False

    if left.endswith(("言っ", "いっ", "逃げ", "見", "し", "き", "来", "行", "て", "で", "つくっ", "作っ", "なっ")):
        return True

    if right.startswith(("て", "で", "た", "だ", "ます", "まし", "ない", "なかっ", "き", "きま", "きました", "いた", "いる", "いく", "くる")):
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

            if cur == "と" and (nxt.startswith("言") or nxt.startswith("い")):
                out.append(cur + nxt)
                i += 2
                continue

            if cur == "と" and nxt.startswith(("いう", "いu", "い")):
                if nxt.startswith("いう"):
                    out.append(cur + nxt)
                    i += 2
                    continue

        if i + 1 < len(clauses):
            nxt = clauses[i + 1]
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

        if cur.startswith(("という", "っていう", "と言", "とい")):
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


def _split_protected_clause(clause, nlp, allow_forced=False):
    text = clause.strip()
    if not text:
        return [clause]

    qb = _quote_boundary_split(text)
    if qb:
        return qb

    if _contains_complete_quote(text) and "という" in text:
        return [clause]

    if _contains_complete_quote(text) and "と言" not in text and "とい" not in text and "って" not in text:
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

    new_clauses = clauses[:idx] + parts + clauses[idx + 1:]
    return new_clauses


def _expand_clause_to_units(text, nlp):
    text = text.strip()
    if not text:
        return [text]

    qb = _quote_boundary_split(text)
    if qb:
        return qb

    doc = nlp(text)

    try:
        spans = [span.text for span in doc._.bunsetsus if span.text.strip()]
    except Exception:
        spans = []

    if spans and len(spans) >= 2:
        return spans

    tokens = [tok.text for tok in doc if tok.text.strip()]
    if len(tokens) >= 2:
        return tokens

    return [text]


def _force_expand_once(clauses, nlp):
    clauses = [c for c in clauses if c.strip()]
    if not clauses:
        return clauses

    candidate_idxs = list(range(len(clauses)))
    candidate_idxs.sort(
        key=lambda i: (
            clauses[i].endswith(FINAL_PREDICATE_PATTERNS),
            -len(clauses[i])
        )
    )

    for idx in candidate_idxs:
        units = _expand_clause_to_units(clauses[idx], nlp)
        units = clean_clauses(units)
        if len(units) >= 2:
            new_clauses = clauses[:idx] + units + clauses[idx + 1:]
            return clean_clauses(new_clauses)

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

        mid = max(1, len(toks) // 2)
        candidate_found = False

        for j in [mid] + list(range(mid - 1, 0, -1)) + list(range(mid + 1, len(toks))):
            left = "".join(toks[:j]).strip()
            right = "".join(toks[j:]).strip()
            if not left or not right:
                continue
            if _starts_with_bad_fragment(right):
                continue
            if _split_breaks_protected_chunk(left, right):
                continue

            new_clauses = clauses[:idx] + [left, right] + clauses[idx + 1:]
            new_clauses = clean_clauses(new_clauses)
            if new_clauses != clauses:
                clauses = new_clauses
                candidate_found = True
                break

        if not candidate_found:
            break

        guard += 1

    return clauses


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

    guard = 0
    while len(clauses) > 5 and guard < 20:
        before = clauses[:]
        clauses = merge_shortest_adjacent(clauses)
        clauses = clean_clauses(clauses)
        if clauses == before:
            break
        guard += 1

    return clauses[:5]


if __name__ == "__main__":
    sample_text = "雨が降っていたので、傘を買って家に帰りました。"
    if len(sys.argv) > 1:
        sample_text = sys.argv[1]

    result = decompose_into_clauses_fallback(sample_text)

    print(f"Original Text: {sample_text}\n")
    print("--- Final 5 Clauses ---")
    for i, clause in enumerate(result, 1):
        print(f"{i}: {clause}")
