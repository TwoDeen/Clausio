import argparse
import json
import sys
from pathlib import Path

from clausify import decompose_into_clauses_fallback


def normalize_expected(expected):
    expected = list(expected[:5])
    while len(expected) < 5:
        expected.append("")
    return expected


def bad_clause_indexes(expected, actual):
    return [i + 1 for i, (e, a) in enumerate(zip(expected, actual)) if e != a]


def run_case(case, show_passes=False):
    corpus_json_id = case.get("corpus_json_id", "")
    sentence = case.get("sentence", "")
    expected = normalize_expected(case.get("expected", []))

    print(f"RUN: {corpus_json_id}", flush=True)

    try:
        actual = decompose_into_clauses_fallback(sentence)
    except Exception as e:
        return {
            "type": "error",
            "corpus_json_id": corpus_json_id,
            "sentence": sentence,
            "expected": expected,
            "error": repr(e),
        }

    actual = normalize_expected(actual)
    joined = "".join(actual)
    count_ok = len(actual) == 5
    reconstruction_ok = joined == sentence
    matches_expected = actual == expected
    bad_indexes = bad_clause_indexes(expected, actual)

    result = {
        "type": "pass" if matches_expected else "failure",
        "corpus_json_id": corpus_json_id,
        "sentence": sentence,
        "expected": expected,
        "actual": actual,
        "joined": joined,
        "count_ok": count_ok,
        "reconstruction_ok": reconstruction_ok,
        "matches_expected": matches_expected,
        "bad_clause_indexes": bad_indexes,
    }

    if show_passes or not matches_expected:
        print(json.dumps(result, ensure_ascii=False), flush=True)

    print(f"DONE: {corpus_json_id}", flush=True)
    return result


def load_jsonl(path):
    cases = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                cases.append(obj)
            except Exception as e:
                print(
                    f"[WARN] Skipping malformed JSONL line {line_no}: {e}",
                    file=sys.stderr,
                    flush=True,
                )
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to JSONL dump file")
    parser.add_argument("--limit", type=int, default=None, help="Only run first N cases")
    parser.add_argument("--start", type=int, default=0, help="Start from case offset")
    parser.add_argument("--show-passes", action="store_true")
    parser.add_argument("--failures-out", default="failures.jsonl")
    args = parser.parse_args()

    cases = load_jsonl(args.file)

    if args.start:
        cases = cases[args.start:]
    if args.limit is not None:
        cases = cases[:args.limit]

    total = 0
    passed = 0
    failed = 0
    errored = 0

    with open(args.failures_out, "w", encoding="utf-8") as fout:
        for case in cases:
            total += 1
            result = run_case(case, show_passes=args.show_passes)

            if result["type"] == "pass":
                passed += 1
            elif result["type"] == "failure":
                failed += 1
                fout.write(json.dumps(result, ensure_ascii=False) + "\n")
            else:
                errored += 1
                fout.write(json.dumps(result, ensure_ascii=False) + "\n")

            if total % 25 == 0:
                print(
                    json.dumps(
                        {
                            "progress": total,
                            "passed": passed,
                            "failed": failed,
                            "errored": errored,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "failure_file": args.failures_out,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
