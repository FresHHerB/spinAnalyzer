"""Performance benchmark for the v2 search engine.

Measures:
    - Per-stage ETL time on a sample of raw XMLs
    - p50/p95/p99 search latency for FAISS k-NN per villain

Usage:
    python scripts/benchmark.py --xml-sample 50 --queries 200
"""

from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path

import numpy as np

from src.context.dp_schema import DecisionPoint
from src.context.extractor_v2 import dps_to_records, extract_decision_points
from src.indexing.build_indices import IndexBuilder
from src.indexing.build_indices_v2 import (
    rebuild_indices,
    write_dps_parquet_partitioned,
)
from src.parsers.pokerkit_adapter import load_phh
from src.parsers.unified_parser import UnifiedParser
from src.vectorization.vectorizer_v2 import vectorize_dp


def time_it(label: str):
    class _T:
        def __enter__(self):
            self.t0 = time.perf_counter()
            return self

        def __exit__(self, *_):
            self.elapsed = time.perf_counter() - self.t0
            print(f"  {label:40s} {self.elapsed:7.2f}s")

    return _T()


def run_benchmark(xml_dir: Path, sample: int, n_queries: int, work_dir: Path) -> None:
    xml_files = sorted(xml_dir.glob("*.xml"))[:sample]
    if not xml_files:
        raise SystemExit(f"no XMLs in {xml_dir}")

    print(f"=== ETL on {len(xml_files)} raw XMLs ===")

    parser = UnifiedParser(output_dir=work_dir / "phh")
    with time_it("parse_xml"):
        phhs: list[Path] = []
        for x in xml_files:
            phhs.extend(parser.parse_file(x, filters={"heads_up_only": True}))
    print(f"    → {len(phhs)} PHHs produced")

    dps: list[DecisionPoint] = []
    with time_it("extract_dps"):
        for f in phhs:
            try:
                dps.extend(extract_decision_points(load_phh(f)))
            except Exception:
                continue
    print(f"    → {len(dps)} DPs")

    with time_it("write_parquet"):
        write_dps_parquet_partitioned(dps, work_dir / "dps")

    with time_it("rebuild_faiss"):
        rebuild_indices(work_dir / "dps", work_dir / "indices")

    # Search benchmark
    print(f"\n=== Search latency over {n_queries} random queries ===")
    builder = IndexBuilder(indices_dir=work_dir / "indices", dimension=99)

    rng = np.random.default_rng(42)
    by_villain: dict[str, list[DecisionPoint]] = {}
    for dp in dps:
        by_villain.setdefault(dp.villain_name, []).append(dp)

    timings: list[float] = []
    for _ in range(n_queries):
        villain = rng.choice(list(by_villain.keys()))
        sample_dp = by_villain[villain][rng.integers(0, len(by_villain[villain]))]
        vec = vectorize_dp(sample_dp).astype(np.float32)
        t0 = time.perf_counter()
        builder.search(villain_name=villain, query_vector=vec, k=20)
        timings.append((time.perf_counter() - t0) * 1000)

    timings.sort()
    p50 = timings[len(timings) // 2]
    p95 = timings[int(len(timings) * 0.95)]
    p99 = timings[int(len(timings) * 0.99)]
    print(f"  n={len(timings)}")
    print(f"  mean   {statistics.mean(timings):6.2f} ms")
    print(f"  p50    {p50:6.2f} ms")
    print(f"  p95    {p95:6.2f} ms")
    print(f"  p99    {p99:6.2f} ms")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--xml-dir", type=Path,
                   default=Path("dataset/original_hands/final"))
    p.add_argument("--xml-sample", type=int, default=50)
    p.add_argument("--queries", type=int, default=200)
    p.add_argument("--work-dir", type=Path,
                   default=Path("/tmp/spin-bench"))
    args = p.parse_args()

    args.work_dir.mkdir(parents=True, exist_ok=True)
    run_benchmark(args.xml_dir, args.xml_sample, args.queries, args.work_dir)


if __name__ == "__main__":
    main()
