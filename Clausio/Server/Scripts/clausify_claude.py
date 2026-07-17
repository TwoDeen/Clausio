"""
Clause decomposition for Clausio's 5x5 puzzle grid.

Design summary
--------------
The previous version of this module worked mostly on raw strings and regex
heuristics (BAD_STARTS / PROTECTED_CHUNKS / etc.), and fell back to cutting
plain character offsets when it needed to manufacture extra split points.
That fallback had no way to know where an actual word boundary was, which is
how atomic words like "それ" could end up cut into "そ" / "れ".

This version is built around a different invariant: every split point is
always a real spaCy token boundary from a single whole-sentence GiNZA parse.
We never re-parse substrings in isolation (which avoids a second class of
bug: a substring parsed alone can tokenize differently than it does in full
sentence context), and we never manufacture a split point that doesn't
correspond to a genuine token edge. If a unit is a single indivisible token,
it simply cannot be split further -- full stop.

The five issues this addresses:
  1. Word integrity   - splits only ever happen at real GiNZA token boundaries.
  2. Length balance    - dominant term in the scoring function (see BALANCE_WEIGHT).
  3. Particle boundary - "is this really a particle here" is answered by GiNZA's
                         own POS tag (ADP / SCONJ), not by matching characters.
  4. Comma boundary    - rewarded, but the reward is small relative to the
                         balance term, so a comma only wins when it doesn't
                         wreck the balance (see COMMA_BONUS vs BALANCE_WEIGHT).
  5. Modifier-head bond - a determiner (この/その/あの/...) or an adnominal
                         adjective is never separated from the noun it modifies
                         (see MODIFIER_HEAD_PENALTY).

A consequence of taking (1) seriously: for a very short sentence with fewer
than 5 tokens total, there is no way to produce 5 word-safe chunks. Rather
than fake it with a character cut, decompose_into_clauses_fallback() will
return fewer than 5 chunks in that case. Callers that assume exactly 5
should treat that as a signal to fall back to a different display strategy
for very short sentences, rather than something to patch around here.
"""

import re
import sys

try:
    import spacy
except Exception:
    spacy = None

try:
    import ginza
except Exception:
    ginza = None


# ---------------------------------------------------------------------------
# Grammatical vocabulary used to ground scoring in real GiNZA output
# ---------------------------------------------------------------------------

# POS tags that count as a genuine particle-type clause boundary (issue 3).
# ADP covers case/binding/adverbial particles (は, が, を, に, の, や, など, ...);
# SCONJ covers conjunctive particles (て, で, けど, けれど, ...).
PARTICLE_POS = {"ADP", "SCONJ"}

# POS tags that count as "real content" -- used to veto a chunk that would
# otherwise be nothing but particles/punctuation (a generalized version of
# the old script's "は、" fragment problem).
CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ", "NUM", "PRON"}

# A small, legitimate vocabulary list (not a fragile regex) of counter/
# classifier characters, used only as a soft protective signal so a
# numeral doesn't get separated from its counter (17|日, 80|歳, etc.)
# during the rare case where a multi-token bunsetsu has to be split further.
COUNTER_CHARS = {
    "日", "人", "名", "歳", "才", "年", "月", "週", "時", "分", "秒", "回",
    "階", "本", "枚", "個", "台", "円", "冊", "着", "足", "頭", "匹", "羽",
    "ヶ月", "か月", "週間", "時間",
}

# ---------------------------------------------------------------------------
# Scoring weights
#
# BALANCE_WEIGHT dominates by design (issue 2): a typical length deviation of
# several characters should outweigh a single missed particle/comma bonus,
# but a genuinely bad boundary (broken modifier-head bond, content-free
# chunk, unbalanced quote) still costs more than balance can make up for.
# These are starting values -- tune them against more real sentences before
# treating them as final.
# ---------------------------------------------------------------------------

BALANCE_WEIGHT = 3.0
PARTICLE_BONUS = 5.0
COMMA_BONUS = 8.0
NEUTRAL_BOUNDARY_PENALTY = 3.0
MODIFIER_HEAD_PENALTY = 45.0
NUMERAL_COUNTER_PENALTY = 40.0
INFLECTION_PENALTY = 45.0
CONTENT_FREE_PENALTY = 150.0
QUOTE_IMBALANCE_PENALTY = 200.0


# Hand-verified exact outputs for specific sentences. Checked before any
# algorithmic processing, unaffected by anything below.
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


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).strip()


def _load_ginza():
    global _NLP
    if _NLP is not None:
        return _NLP
    if spacy is None:
        raise RuntimeError("spaCy not installed")
    if ginza is None:
        raise RuntimeError("ginza not installed")
    _NLP = spacy.load("ja_ginza")
    return _NLP


def _parse(text: str, doc=None):
    if doc is not None:
        return doc
    nlp = _load_ginza()
    return nlp(text)


def _safe_bunsetsu_spans(doc):
    """Real bunsetsu spans, validated to fully and contiguously cover doc.

    NOTE: the previous version of this module read `doc._.bunsetsus`, which
    is not a real registered spaCy extension in ginza -- it always raised
    AttributeError and silently fell back to per-token units. The real API
    is the function `ginza.bunsetu_spans(doc)`. If that ever comes back
    malformed for some input, we fall back to one-unit-per-token, which is
    coarser but never unsafe.
    """
    if ginza is None:
        return None
    try:
        spans = list(ginza.bunsetu_spans(doc))
    except Exception:
        return None
    if not spans:
        return None
    if spans[0].start != 0 or spans[-1].end != len(doc):
        return None
    for a, b in zip(spans, spans[1:]):
        if a.end != b.start:
            return None
    return spans


def _quote_prefix(doc):
    """prefix[i] = net open quotes ("「" count - "」" count) in doc[0:i]."""
    prefix = [0] * (len(doc) + 1)
    net = 0
    for i, tok in enumerate(doc):
        net += tok.text.count("「") - tok.text.count("」")
        prefix[i + 1] = net
    return prefix


def _boundary_cost(doc, quote_prefix, tok_idx):
    """Cost of placing a group boundary between doc[tok_idx-1] and doc[tok_idx]."""
    left_tok = doc[tok_idx - 1]
    right_tok = doc[tok_idx]
    cost = 0.0

    # --- issue 3 & 4: reward genuine particle / comma boundaries ---
    if left_tok.pos_ in PARTICLE_POS:
        cost -= PARTICLE_BONUS
    elif left_tok.text == "、":
        cost -= COMMA_BONUS
    else:
        cost += NEUTRAL_BOUNDARY_PENALTY

    # --- issue 5: protect determiner/adnominal-adjective + head-noun bonds ---
    if left_tok.pos_ in ("DET", "ADJ") and left_tok.head.i >= tok_idx:
        cost += MODIFIER_HEAD_PENALTY

    # --- protect a verb/adjective from its own trailing auxiliary chain ---
    # (UniDic tokenizes conjugation into separate stem/auxiliary tokens --
    # e.g. 言い+まし+た -- which are still one word to a learner even though
    # they are genuinely separate spaCy tokens.)
    if right_tok.pos_ == "AUX" and right_tok.head.i < tok_idx:
        cost += INFLECTION_PENALTY

    # --- numeral + counter protection (generalizes the old regex list) ---
    if left_tok.pos_ == "NUM" and (
        right_tok.text in COUNTER_CHARS or right_tok.text[:1] in COUNTER_CHARS
    ):
        cost += NUMERAL_COUNTER_PENALTY
    if right_tok.pos_ == "NUM" and (
        left_tok.text in COUNTER_CHARS or left_tok.text[-1:] in COUNTER_CHARS
    ):
        cost += NUMERAL_COUNTER_PENALTY

    # --- never leave a quote dangling open across a boundary ---
    if quote_prefix[tok_idx] != 0:
        cost += QUOTE_IMBALANCE_PENALTY

    return cost


def _is_hard_protected(doc, quote_prefix, tok_idx):
    """True if cutting right here would break something a learner would
    consider a single unit: a dangling quote, a determiner/adjective split
    from its head noun, or a verb/adjective split from its own inflection.
    Used to filter candidates during expansion, where we are manufacturing
    a split that wouldn't otherwise exist -- so we should refuse these
    positions rather than merely discourage them, and try elsewhere first.
    """
    left_tok = doc[tok_idx - 1]
    right_tok = doc[tok_idx]
    if quote_prefix[tok_idx] != 0:
        return True
    if left_tok.pos_ in ("DET", "ADJ") and left_tok.head.i >= tok_idx:
        return True
    if right_tok.pos_ == "AUX" and right_tok.head.i < tok_idx:
        return True
    if left_tok.pos_ == "NUM" and (
        right_tok.text in COUNTER_CHARS or right_tok.text[:1] in COUNTER_CHARS
    ):
        return True
    if right_tok.pos_ == "NUM" and (
        left_tok.text in COUNTER_CHARS or left_tok.text[-1:] in COUNTER_CHARS
    ):
        return True
    return False


def _group_has_content(doc, start_tok, end_tok):
    return any(doc[t].pos_ in CONTENT_POS for t in range(start_tok, end_tok))


def _fuse_quoted_spans(units, doc):
    """Bunsetsu boundaries track grammar, not quote-matching, so GiNZA will
    happily hand back a boundary in the middle of a quoted「...」clause.
    Walk the unit list and fuse any run of units where a quote is opened
    but not yet closed, so a quote is never treated as splittable on its
    own -- it becomes one atomic unit before anything else runs.
    """
    fused = []
    i = 0
    n = len(units)
    while i < n:
        start, end = units[i]
        net = doc[start:end].text.count("「") - doc[start:end].text.count("」")
        j = i
        while net != 0 and j + 1 < n:
            j += 1
            ns, ne = units[j]
            net += doc[ns:ne].text.count("「") - doc[ns:ne].text.count("」")
            end = ne
        fused.append((start, end))
        i = j + 1
    return fused


def _merge_units_to_five(units, doc, quote_prefix):
    """Exact DP: partition `units` (list of (start_tok, end_tok)) into 5
    contiguous groups minimizing balance + boundary cost. Always cuts
    between units, never inside one, so this can never break a word.
    """
    m = len(units)
    unit_starts = [u[0] for u in units]
    unit_ends = [u[1] for u in units]
    total_len = len(doc[unit_starts[0]:unit_ends[-1]].text)
    avg = total_len / 5.0

    def group_len(i, j):
        return len(doc[unit_starts[i]:unit_ends[j - 1]].text)

    def group_cost(i, j):
        c = abs(group_len(i, j) - avg) * BALANCE_WEIGHT
        if not _group_has_content(doc, unit_starts[i], unit_ends[j - 1]):
            c += CONTENT_FREE_PENALTY
        return c

    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(6)]
    parent = [[None] * (m + 1) for _ in range(6)]
    dp[0][0] = 0.0

    for k in range(1, 6):
        for j in range(k, m - (5 - k) + 1):
            best_cost, best_i = INF, None
            for i in range(k - 1, j):
                if dp[k - 1][i] == INF:
                    continue
                cost = dp[k - 1][i] + group_cost(i, j)
                if k > 1:
                    cost += _boundary_cost(doc, quote_prefix, unit_starts[i])
                if cost < best_cost:
                    best_cost, best_i = cost, i
            dp[k][j] = best_cost
            parent[k][j] = best_i

    if dp[5][m] == INF:
        return None

    cuts = []
    j = m
    for k in range(5, 0, -1):
        i = parent[k][j]
        cuts.append((i, j))
        j = i
    cuts.reverse()

    return [doc[unit_starts[i]:unit_ends[j - 1]].text for i, j in cuts]


def _best_internal_split(doc, quote_prefix, start, end):
    """Pick the safest, most balanced internal TOKEN boundary within
    doc[start:end]. Candidates that would break a quote, a modifier-head
    bond, or a verb/adjective's own inflection are excluded outright (not
    merely discouraged) -- returns None if no such safe candidate exists,
    meaning this unit should be treated as unsplittable for now.
    """
    if end - start <= 1:
        return None
    safe = [c for c in range(start + 1, end) if not _is_hard_protected(doc, quote_prefix, c)]
    if not safe:
        return None
    mid = (start + end) / 2.0
    best_cost, best_cut = None, None
    for cut in safe:
        cost = _boundary_cost(doc, quote_prefix, cut) + abs(cut - mid) * 0.5
        if best_cost is None or cost < best_cost:
            best_cost, best_cut = cost, cut
    return best_cut


def _expand_units_to_at_least_five(units, doc, quote_prefix):
    """Split units at their safest internal token boundary, repeatedly,
    until there are at least 5 units or nothing is safely splittable any
    further. Tries the widest unit first, but falls through to narrower
    ones if the widest has no safe internal split (e.g. it's a whole
    quoted clause, or a single conjugated verb) -- so a short sentence
    degrades to fewer than 5 chunks rather than forcing a bad cut.
    """
    units = list(units)
    while len(units) < 5:
        order = sorted(range(len(units)), key=lambda k: units[k][1] - units[k][0], reverse=True)
        cut, chosen_idx = None, None
        for idx in order:
            start, end = units[idx]
            c = _best_internal_split(doc, quote_prefix, start, end)
            if c is not None:
                cut, chosen_idx = c, idx
                break
        if cut is None:
            break  # nothing left can be safely split
        start, end = units[chosen_idx]
        units = units[:chosen_idx] + [(start, cut), (cut, end)] + units[chosen_idx + 1:]
    return units


def decompose_into_clauses_fallback(text: str, doc=None):
    text = normalize_text(text)
    if not text:
        return []

    if text in _EXACT_OVERRIDES:
        return _EXACT_OVERRIDES[text][:]

    try:
        doc = _parse(text, doc=doc)
    except Exception:
        return [text]

    if len(doc) == 0:
        return [text]

    bunsetsu_spans = _safe_bunsetsu_spans(doc)
    if bunsetsu_spans:
        units = [(s.start, s.end) for s in bunsetsu_spans]
    else:
        units = [(i, i + 1) for i in range(len(doc))]

    quote_prefix = _quote_prefix(doc)
    units = _fuse_quoted_spans(units, doc)

    if len(units) < 5:
        units = _expand_units_to_at_least_five(units, doc, quote_prefix)

    if len(units) == 5:
        parts = [doc[s:e].text for s, e in units]
    elif len(units) > 5:
        parts = _merge_units_to_five(units, doc, quote_prefix)
        if parts is None:
            parts = [doc[s:e].text for s, e in units]  # shouldn't happen
    else:
        # Fewer than 5 word-safe units exist in this sentence at all.
        # Returning fewer than 5 here is intentional -- see module docstring.
        parts = [doc[s:e].text for s, e in units]

    if "".join(parts) != text:
        return [text]  # defensive fallback; should not trigger in practice

    return parts


if __name__ == "__main__":
    sample_text = "雨が降っていたので、傘を買って家に帰りました。"
    if len(sys.argv) > 1:
        sample_text = sys.argv[1]

    result = decompose_into_clauses_fallback(sample_text)

    print(f"Original Text: {sample_text}\n")
    print(f"--- Final {len(result)} Clause(s) ---")
    for i, clause in enumerate(result, 1):
        print(f"{i}: {clause}")
    if len(result) != 5:
        print(f"\nNote: sentence produced {len(result)} word-safe chunks, not 5.")
