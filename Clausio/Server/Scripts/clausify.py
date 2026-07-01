import sys
import re
import spacy


LEADING_CLOSERS = "」』】）》］〕〙〗〟’”）】"
TRAILING_OPENERS = "「『【《［〔〘〖〝‘“（【"

BAD_PREV_TOKENS = {
    "は", "が", "を", "に", "で", "と", "へ", "も", "の", "や", "か", "ね", "よ", "ぞ", "さ",
    "て", "で", "な", "し", "ては", "では"
}

BAD_NEXT_TOKENS = {
    "た", "だ", "です", "ます", "ない", "たい", "られる", "れる",
    "て", "で", "う", "よう", "そう"
}

BAD_POS_CHAINS = {"AUX", "VERB", "SCONJ", "CCONJ", "PART"}


def _load_nlp():
    try:
        return spacy.load("ja_ginza")
    except OSError:
        print(
            "Error: GiNZA model not found. Please install it using: pip install ja-ginza",
            file=sys.stderr
        )
        return None


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "").strip()


def _rebalance_quotes_and_punct(clauses: list[str]) -> list[str]:
    if not clauses:
        return clauses

    out = clauses[:]

    # Move leading closing punctuation back to previous clause
    for i in range(1, len(out)):
        while out[i] and out[i][0] in LEADING_CLOSERS:
            ch = out[i][0]
            out[i] = out[i][1:]
            out[i - 1] += ch

    # Move trailing opening quotes forward to next clause
    for i in range(len(out) - 1):
        while out[i] and out[i][-1] in TRAILING_OPENERS:
            ch = out[i][-1]
            out[i] = out[i][:-1]
            out[i + 1] = ch + out[i + 1]

    # Trim empties if punctuation shuffling created any
    out = [c for c in out if c]

    return out


def _safe_split_points(text: str, nlp) -> list[int]:
    doc = nlp(text)
    points = []

    for i in range(len(doc) - 1):
        token = doc[i]
        nxt = doc[i + 1]

        split_idx = token.idx + len(token.text)

        if split_idx <= 0 or split_idx >= len(text):
            continue

        # Do not let next clause start with closing punctuation
        while split_idx < len(text) and text[split_idx] in LEADING_CLOSERS + "、。！？":
            split_idx += 1

        if split_idx <= 0 or split_idx >= len(text):
            continue

        prev_text = token.text
        next_text = nxt.text
        prev_pos = token.pos_
        next_pos = nxt.pos_

        # Avoid splits after dangling particles/connectors
        if prev_text in BAD_PREV_TOKENS:
            continue

        # Avoid starting next clause with auxiliaries / endings
        if next_text in BAD_NEXT_TOKENS:
            continue

        # Avoid splitting inside verb/aux chains
        if prev_pos in BAD_POS_CHAINS and next_pos in BAD_POS_CHAINS:
            continue

        # Avoid splits right around quote glue like と言っ / 」と言っ
        if prev_text in {"と", "って"}:
            continue
        if next_text in {"言っ", "いっ", "言う", "いう", "て", "た"}:
            continue

        points.append(split_idx)

    return sorted(set(points))


def split_longest_clause(clauses: list[str], nlp) -> list[str]:
    if not clauses:
        return clauses

    longest_idx = max(range(len(clauses)), key=lambda i: len(clauses[i]))
    text_to_split = clauses[longest_idx]

    if len(text_to_split) <= 1:
        return clauses

    best_split_idx = -1
    min_dist_to_mid = float("inf")
    mid_point = len(text_to_split) / 2

    for split_idx in _safe_split_points(text_to_split, nlp):
        dist = abs(split_idx - mid_point)
        if dist < min_dist_to_mid:
            min_dist_to_mid = dist
            best_split_idx = split_idx

    if best_split_idx == -1:
        doc = nlp(text_to_split)
        bunsetsu_like = []
        try:
            for span in doc._.bunsetsus:
                bunsetsu_like.append(span.text)
        except AttributeError:
            bunsetsu_like = [t.text for t in doc]

        if len(bunsetsu_like) >= 2:
            running = 0
            best_boundary = -1
            best_dist = float("inf")

            for part in bunsetsu_like[:-1]:
                running += len(part)
                if running <= 0 or running >= len(text_to_split):
                    continue
                if text_to_split[running:running+1] in LEADING_CLOSERS:
                    continue
                dist = abs(running - mid_point)
                if dist < best_dist:
                    best_dist = dist
                    best_boundary = running

            best_split_idx = best_boundary

    if best_split_idx == -1:
        mid = max(1, len(text_to_split) // 2)

        while mid < len(text_to_split) and text_to_split[mid] in LEADING_CLOSERS + "、。！？":
            mid += 1

        if mid >= len(text_to_split):
            mid = max(1, len(text_to_split) // 2)

        best_split_idx = mid

    part1 = text_to_split[:best_split_idx]
    part2 = text_to_split[best_split_idx:]

    new_parts = _rebalance_quotes_and_punct([part1, part2])

    if len(new_parts) == 2 and all(new_parts):
        clauses[longest_idx:longest_idx + 1] = new_parts

    return _rebalance_quotes_and_punct(clauses)


def merge_shortest_adjacent(clauses: list[str]) -> list[str]:
    if len(clauses) <= 1:
        return clauses

    min_len = float("inf")
    merge_idx = -1

    for i in range(len(clauses) - 1):
        combined_len = len(clauses[i]) + len(clauses[i + 1])
        if combined_len < min_len:
            min_len = combined_len
            merge_idx = i

    clauses[merge_idx] = clauses[merge_idx] + clauses[merge_idx + 1]
    del clauses[merge_idx + 1]

    return _rebalance_quotes_and_punct(clauses)


def _initial_bunsetsu_clauses(text: str, nlp) -> list[str]:
    doc = nlp(text)
    initial_clauses = []

    try:
        for span in doc._.bunsetsus:
            if span.text:
                initial_clauses.append(span.text)
    except AttributeError:
        for token in doc:
            if token.text:
                initial_clauses.append(token.text)

    if not initial_clauses:
        initial_clauses = [text]

    return _rebalance_quotes_and_punct(initial_clauses)


def decompose_into_clauses_fallback(text: str) -> list[str]:
    nlp = _load_nlp()
    if nlp is None:
        return []

    text = _normalize_text(text)
    if not text:
        return []

    clauses = _initial_bunsetsu_clauses(text, nlp)

    while len(clauses) > 5:
        clauses = merge_shortest_adjacent(clauses)

    guard = 0
    while len(clauses) < 5 and guard < 20:
        before = clauses[:]
        clauses = split_longest_clause(clauses, nlp)
        clauses = _rebalance_quotes_and_punct(clauses)
        if clauses == before:
            break
        guard += 1

    clauses = [c.strip() for c in clauses if c and c.strip()]
    clauses = _rebalance_quotes_and_punct(clauses)

    # Last-resort exact-5 enforcement
    while len(clauses) > 5:
        clauses = merge_shortest_adjacent(clauses)

    while len(clauses) < 5:
        longest_idx = max(range(len(clauses)), key=lambda i: len(clauses[i]))
        chunk = clauses[longest_idx]

        if len(chunk) <= 1:
            break

        split_at = max(1, len(chunk) // 2)
        while split_at < len(chunk) and chunk[split_at] in LEADING_CLOSERS + "、。！？":
            split_at += 1
        if split_at >= len(chunk):
            split_at = max(1, len(chunk) // 2)

        part1 = chunk[:split_at]
        part2 = chunk[split_at:]
        repaired = _rebalance_quotes_and_punct([part1, part2])

        if len(repaired) != 2 or not repaired[0] or not repaired[1]:
            break

        clauses[longest_idx:longest_idx + 1] = repaired
        clauses = _rebalance_quotes_and_punct(clauses)

    return clauses[:5]


if __name__ == "__main__":
    sample_text = "男性は「助けてほしい」と言って、近くの家に逃げてきました。"
    if len(sys.argv) > 1:
        sample_text = sys.argv[1]

    result_clauses = decompose_into_clauses_fallback(sample_text)

    print(f"Original Text: {sample_text}\n")
    print("--- Final 5 Clauses ---")
    for i, clause in enumerate(result_clauses, 1):
        print(f"{i}: {clause}")
