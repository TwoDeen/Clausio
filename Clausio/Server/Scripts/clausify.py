import sys
import re
import spacy


CASE_PARTICLES = ("は", "が", "を", "に", "へ", "で", "と", "も", "から", "まで", "より", "の")
BOUNDARY_ENDINGS = CASE_PARTICLES + ("、", "」")
PREDICATE_ENDINGS = (
    "ました。", "ます。", "でした。", "です。", "だ。", "だった。",
    "ません。", "ない。", "なかった。", "ている。", "ていた。",
    "てきた。", "てきました。", "している。", "していた。"
)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).strip()


def merge_shortest_adjacent(clauses):
    if len(clauses) < 2:
        return clauses

    min_len = float("inf")
    merge_idx = 0

    for i in range(len(clauses) - 1):
        combined_len = len(clauses[i]) + len(clauses[i + 1])
        if combined_len < min_len:
            min_len = combined_len
            merge_idx = i

    clauses[merge_idx] = clauses[merge_idx] + clauses[merge_idx + 1]
    del clauses[merge_idx + 1]
    return clauses


def is_complete_quote(text: str) -> bool:
    return "「" in text and "」" in text


def is_protected_predicate(text: str) -> bool:
    s = text.strip()

    if s.endswith(PREDICATE_ENDINGS):
        return True

    protected_patterns = (
        "てきました", "ていました", "てしまいました", "と言って", "といって",
        "と言いました", "と話しました", "と思います", "になりました",
        "していました", "されました", "してきました"
    )
    return any(p in s for p in protected_patterns)


def split_quoted_span(text: str):
    m = re.search(r"「[^」]+」", text)
    if not m:
        return None

    left = text[:m.start()]
    quoted = text[m.start():m.end()]
    right = text[m.end():]

    out = []
    if left:
        out.append(left)
    out.append(quoted)
    if right:
        out.append(right)
    return out


def split_after_best_particle(text: str):
    candidates = []

    for p in CASE_PARTICLES:
        start = 0
        while True:
            idx = text.find(p, start)
            if idx == -1:
                break

            split_idx = idx + len(p)
            if 0 < split_idx < len(text):
                left = text[:split_idx]
                right = text[split_idx:]
                if left and right:
                    score = abs(len(text) / 2 - split_idx)
                    candidates.append((score, left, right))
            start = idx + 1

    if not candidates:
        return [text]

    _, left, right = sorted(candidates, key=lambda x: x[0])[0]
    return [left, right]


def merge_special_units(clauses):
    out = []
    i = 0

    while i < len(clauses):
        cur = clauses[i]

        # Merge quote + と言って... as separate desired units:
        # keep 「...」 intact, but allow following clause to begin with と言...
        if i + 1 < len(clauses):
            nxt = clauses[i + 1]

            # Merge broken quotative phrase
            if cur == "と" and (nxt.startswith("言") or nxt.startswith("い")):
                out.append(cur + nxt)
                i += 2
                continue

            # Merge broken predicate chain
            if (
                cur.endswith(("言っ", "いっ", "逃げ", "見", "し", "て", "で", "き"))
                or nxt.startswith(("て", "で", "き", "きま", "きました", "ました", "ます", "た", "だ"))
            ):
                combined = cur + nxt
                if is_protected_predicate(combined) or not cur.endswith(BOUNDARY_ENDINGS):
                    out.append(combined)
                    i += 2
                    continue

        out.append(cur)
        i += 1

    return out


def initial_rule_based_split(text: str):
    quoted = split_quoted_span(text)

    if quoted:
        clauses = []
        left = ""
        quote = ""
        right = ""

        if len(quoted) == 3:
            left, quote, right = quoted
        elif len(quoted) == 2:
            if quoted[0].startswith("「"):
                quote, right = quoted
            else:
                left, quote = quoted
        else:
            quote = quoted[0]

        if left:
            clauses.extend(split_after_best_particle(left))

        clauses.append(quote)

        if right:
            # Prefer separating と言って、 first
            m = re.match(r"^(と(?:言|い)[^、。]*[、]?)", right)
            if m:
                first = m.group(1)
                rest = right[len(first):]
                clauses.append(first)
                if rest:
                    clauses.extend(split_after_best_particle(rest))
            else:
                clauses.extend(split_after_best_particle(right))

        return [c for c in clauses if c]

    return split_after_best_particle(text)


def rank_split_candidates(text: str, nlp):
    doc = nlp(text)
    candidates = []

    for token in doc:
        split_idx = token.idx + len(token.text)

        if not (0 < split_idx < len(text)):
            continue

        left = text[:split_idx]
        right = text[split_idx:]

        if not left or not right:
            continue

        # Never split inside complete quote
        if ("「" in left and "」" not in left) or ("」" in right and "「" not in right):
            continue

        # Strongly prefer left chunks that end on particles/punctuation
        quality = 100

        if left.endswith(CASE_PARTICLES):
            quality = 0
        elif left.endswith(("、", "」")):
            quality = 1
        elif token.text in CASE_PARTICLES:
            quality = 2

        # Protect predicate on the right
        if is_protected_predicate(right):
            quality -= 10

        # Avoid ugly predicate break like 近くの家に逃 | げてきました。
        if right.startswith(("げ", "き", "まし", "ました", "て", "で", "た", "だ")) and not left.endswith(BOUNDARY_ENDINGS):
            continue

        candidates.append((quality, abs(len(text) / 2 - split_idx), split_idx))

    return sorted(candidates)


def split_longest_clause_safely(clauses, nlp):
    eligible = []

    for i, clause in enumerate(clauses):
        s = clause.strip()

        if len(s) <= 2:
            continue
        if is_complete_quote(s):
            continue
        if is_protected_predicate(s):
            continue

        eligible.append(i)

    if not eligible:
        return clauses

    idx = max(eligible, key=lambda i: len(clauses[i]))
    target = clauses[idx]

    candidates = rank_split_candidates(target, nlp)
    if not candidates:
        return clauses

    split_idx = candidates[0][2]
    left = target[:split_idx]
    right = target[split_idx:]

    if not left or not right:
        return clauses

    clauses[idx:idx + 1] = [left, right]
    return clauses


def decompose_into_clauses_fallback(text):
    try:
        nlp = spacy.load("ja_ginza")
    except OSError:
        print("Error: GiNZA model not found. Please install it using: pip install ja-ginza", file=sys.stderr)
        return []

    text = normalize_text(text)
    clauses = initial_rule_based_split(text)

    prev = None
    while prev != clauses:
        prev = clauses[:]
        clauses = merge_special_units(clauses)

    while len(clauses) > 5:
        clauses = merge_shortest_adjacent(clauses)

    guard = 0
    while len(clauses) < 5 and guard < 10:
        new_clauses = split_longest_clause_safely(clauses, nlp)
        if new_clauses == clauses:
            break
        clauses = new_clauses
        guard += 1

    # Final fallback: only split at safe visible boundaries, never midpoint-chop predicates
    guard = 0
    while len(clauses) < 5 and guard < 10:
        changed = False

        for i, clause in enumerate(clauses):
            s = clause.strip()

            if is_complete_quote(s) or is_protected_predicate(s):
                continue

            split_points = []
            for j in range(1, len(s)):
                left = s[:j]
                right = s[j:]
                if left.endswith(BOUNDARY_ENDINGS) and right:
                    split_points.append((abs(len(s) / 2 - j), j))

            if split_points:
                j = sorted(split_points, key=lambda x: x[0])[0][1]
                clauses[i:i + 1] = [s[:j], s[j:]]
                changed = True
                break

        if not changed:
            break
        guard += 1

    # Absolute contract fallback for pipeline compatibility
    while len(clauses) < 5:
        clauses.append("")

    clauses = clauses[:5]

    # Avoid empty strings reaching the grid if possible
    for i, c in enumerate(clauses):
        if not c:
            clauses[i] = "…"

    return clauses


if __name__ == "__main__":
    sample_text = "雨が降っていたので、傘を買って家に帰りました。"
    if len(sys.argv) > 1:
        sample_text = sys.argv[1]

    result_clauses = decompose_into_clauses_fallback(sample_text)

    print(f"Original Text: {sample_text}\n")
    print("--- Final 5 Clauses ---")
    for i, clause in enumerate(result_clauses, 1):
        print(f"{i}: {clause}")
