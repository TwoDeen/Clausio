import argparse
import csv
import importlib.util
import json
import statistics
import time
from pathlib import Path
from typing import Optional

DEFAULT_SENTENCES = [
    "今日は天気がとてもいいです。",
    "17日午前6時ごろ、石川県小松市の山の近くで、熊が80歳ぐらいの男性を襲いました。",
    "男性は「助けてほしい」と言って、近くの家に逃げてきました。",
    "私は昨日、友だちと映画を見て、そのあとでご飯を食べました。",
    "雨が降っていたので、傘を買って家に帰りました。",
]


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    spec.loader.exec_module(module)
    return module


def load_sentences(path: Optional[Path]):
    if path is None:
        return DEFAULT_SENTENCES

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return DEFAULT_SENTENCES

    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, list):
            if data and isinstance(data[0], dict) and "sentence" in data[0]:
                return [item["sentence"] for item in data if item.get("sentence")]
            return [str(x) for x in data]
        raise ValueError("JSON file must contain a list")

    return [line.strip() for line in text.splitlines() if line.strip()]


def benchmark_function(func, sentences, loops, warmups):
    per_call = []

    for _ in range(warmups):
        for s in sentences:
            func(s)

    total_start = time.perf_counter()
    for _ in range(loops):
        for s in sentences:
            t0 = time.perf_counter()
            func(s)
            per_call.append(time.perf_counter() - t0)
    total_elapsed = time.perf_counter() - total_start

    result = {
        "calls": len(per_call),
        "total_sec": total_elapsed,
        "avg_ms": statistics.mean(per_call) * 1000,
        "median_ms": statistics.median(per_call) * 1000,
        "min_ms": min(per_call) * 1000,
        "max_ms": max(per_call) * 1000,
        "p95_ms": None,
    }

    if len(per_call) >= 100:
        result["p95_ms"] = statistics.quantiles(per_call, n=100)[94] * 1000

    return result


def main():
    parser = argparse.ArgumentParser(description="Benchmark clausify.py vs clausify_alt.py")
    parser.add_argument("--clausify", default="clausify.py", help="Path to clausify.py")
    parser.add_argument("--alt", default="clausify_alt.py", help="Path to clausify_alt.py")
    parser.add_argument("--sentences", default=None, help="Optional .txt or .json file with benchmark sentences")
    parser.add_argument("--loops", type=int, default=20, help="Number of benchmark loops over the sentence set")
    parser.add_argument("--warmups", type=int, default=2, help="Number of warmup loops")
    parser.add_argument("--output", default="benchmark_clausify_results.csv", help="Output CSV path")
    args = parser.parse_args()

    clausify_path = Path(args.clausify)
    alt_path = Path(args.alt)
    sentences_path = Path(args.sentences) if args.sentences else None

    sentences = load_sentences(sentences_path)

    modules = [
        ("clausify.py", load_module(clausify_path, "clausify_mod")),
        ("clausify_alt.py", load_module(alt_path, "clausify_alt_mod")),
    ]

    rows = []
    for label, module in modules:
        func = getattr(module, "decompose_into_clauses_fallback")
        stats = benchmark_function(func, sentences, args.loops, args.warmups)
        row = {
            "file": label,
            "sentences": len(sentences),
            "loops": args.loops,
            **stats,
        }
        rows.append(row)

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file", "sentences", "loops", "calls",
                "total_sec", "avg_ms", "median_ms",
                "min_ms", "max_ms", "p95_ms"
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("Benchmark complete.\n")
    for row in rows:
        print(row["file"])
        print("  sentences: {}".format(row["sentences"]))
        print("  loops:     {}".format(row["loops"]))
        print("  calls:     {}".format(row["calls"]))
        print("  total_sec: {:.6f}".format(row["total_sec"]))
        print("  avg_ms:    {:.3f}".format(row["avg_ms"]))
        print("  median_ms: {:.3f}".format(row["median_ms"]))
        print("  min_ms:    {:.3f}".format(row["min_ms"]))
        print("  max_ms:    {:.3f}".format(row["max_ms"]))
        if row["p95_ms"] is not None:
            print("  p95_ms:    {:.3f}".format(row["p95_ms"]))
        print()

    faster = min(rows, key=lambda r: r["avg_ms"])
    print("Faster by average elapsed time: {}".format(faster["file"]))
    print("CSV written to: {}".format(args.output))


if __name__ == "__main__":
    main()
