#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

URLISH_RE = re.compile(r"https?://|www\.|tadoku\.info", re.IGNORECASE)
ONLY_DIGITS_RE = re.compile(r"^[0-9０-９]+$")
ONLY_SYMBOLS_RE = re.compile(r"^[\W_]+$", re.UNICODE)


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_grid_items(data):
    grid = data.get("grid_matrix")
    if grid is None:
        grid = data.get("gridMatrix")
    return grid or []


def get_corpus_json_id(data):
    corpus_ref = data.get("corpus_ref")
    if corpus_ref is None:
        corpus_ref = data.get("corpusRef") or {}
    return corpus_ref.get("corpus_json_id") or corpus_ref.get("corpusJsonId") or ""


def normalize_clause(text):
    if text is None:
        return ""
    return str(text).strip()


def grouped_rows(gridmatrix):
    rows = {}
    for item in gridmatrix or []:
        if not isinstance(item, dict):
            continue

        coords = item.get("grid_coordinates")
        if coords is None:
            coords = item.get("gridCoordinates") or {}

        row = coords.get("row")
        col = coords.get("column")
        if row is None or col is None:
            continue

        text = item.get("clause_text")
        if text is None:
            text = item.get("clauseText", "")

        rows.setdefault(row, {})[col] = normalize_clause(text)
    return rows


def is_noise_row(expected):
    expected = [normalize_clause(x) for x in expected]
    nonempty = [x for x in expected if x]

    if len(expected) != 5:
        return True
    if len(nonempty) < 5:
        return True

    sentence = "".join(expected).strip()
    if not sentence:
        return True
    if URLISH_RE.search(sentence):
        return True
    if all(ONLY_DIGITS_RE.fullmatch(x) for x in nonempty):
        return True
    if all(ONLY_SYMBOLS_RE.fullmatch(x) for x in nonempty):
        return True
    return False


def emit_for_file(path, include_noise=False):
    data = load_json(path)
    grid = get_grid_items(data)
    corpus_json_id = get_corpus_json_id(data)
    rows = grouped_rows(grid)
    out = []

    for row_num in sorted(rows):
        cols = rows[row_num]
        expected = [normalize_clause(cols.get(i, "")) for i in range(1, 6)]
        if not include_noise and is_noise_row(expected):
            continue

        sentence = "".join(expected)
        obj = {
            "corpus_json_id": corpus_json_id or f"{path.stem}#{row_num}",
            "sentence": sentence,
            "expected": expected,
            "source_file": path.name,
            "row": row_num,
        }
        out.append(json.dumps(obj, ensure_ascii=False))
    return out


def resolve_targets(base_dir, filename):
    if filename:
        p = Path(filename)
        if not p.is_absolute():
            p = base_dir / filename
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")
        return [p]
    return sorted(base_dir.glob("*.json"))


def main():
    parser = argparse.ArgumentParser(
        description="Dump Tadoku rows for clausify debugging as JSONL"
    )
    parser.add_argument("--dir", default="precomputed/corpus/tadoku")
    parser.add_argument("--file", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--include-noise", action="store_true")
    args = parser.parse_args()

    base_dir = Path(args.dir)
    if not base_dir.exists():
        raise SystemExit(f"Directory not found: {base_dir}")

    targets = resolve_targets(base_dir, args.file)
    lines = []

    for path in targets:
        lines.extend(emit_for_file(path, include_noise=args.include_noise))

    text = "\n".join(lines)
    if text:
        text += "\n"

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
