import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
INDEX_CANDIDATES = [
    ROOT / "corpus_index.json",
    ROOT / "precomputed" / "corpus_index.json",
]
OUT_PATH = ROOT / "sentence-clauses.txt"


def load_index():
    for path in INDEX_CANDIDATES:
        if path.exists():
            with path.open(encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("corpus_index.json not found")


def iter_entries(obj):
    if isinstance(obj, dict):
        if "corpus_json_path" in obj:
            yield obj
        for value in obj.values():
            yield from iter_entries(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_entries(item)


def extract_sentence_lines_from_grid_matrix(data):
    grid = data.get("grid_matrix", [])
    grouped = defaultdict(dict)

    for item in grid:
        sentence_id = item.get("parent_sentence_id")
        column = item.get("grid_coordinates", {}).get("column")
        clause_text = item.get("clause_text", "")

        if sentence_id is None or column is None:
            continue
        grouped[sentence_id][column] = clause_text

    lines = []
    for sentence_id in sorted(grouped):
        row = grouped[sentence_id]
        clauses = [row.get(i, "") for i in range(1, 6)]
        sentence = "".join(clauses)
        lines.append(f"{sentence}:{'/'.join(clauses)}")
    return lines


def main():
    index = load_index()
    lines = []
    corpus_files_seen = 0
    missing_files = 0

    for entry in iter_entries(index):
        rel = entry.get("corpus_json_path")
        if not rel:
            continue

        path = ROOT / rel
        if not path.exists():
            missing_files += 1
            continue

        corpus_files_seen += 1
        with path.open(encoding="utf-8") as f:
            data = json.load(f)

        lines.extend(extract_sentence_lines_from_grid_matrix(data))

    OUT_PATH.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"wrote {len(lines)} lines to {OUT_PATH}")
    print(f"corpus files processed: {corpus_files_seen}")
    print(f"missing corpus files: {missing_files}")


if __name__ == "__main__":
    main()
