#!/usr/bin/env python3
"""Manual benchmark for MySQL connection pooling.

The benchmark only runs `SELECT 1`; it does not mutate schema or data.
"""

from __future__ import annotations

import concurrent.futures
import math
import os
import sys
import time
from dataclasses import dataclass

import mysql.connector
from dotenv import load_dotenv


sys.path.append(os.getcwd())
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "chuongdev_admin"),
    "password": os.getenv("DB_PASSWORD", "Chuong2004@"),
    "database": os.getenv("DB_DATABASE", "flask_app"),
    "autocommit": True,
}

NUM_SESSIONS = int(os.getenv("DB_BENCHMARK_SESSIONS", "30"))
QUERY = "SELECT 1"

import config.database as database


@dataclass(frozen=True)
class Sample:
    ok: bool
    latency_ms: float
    error: str = ""


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil((percent / 100) * len(ordered)) - 1)
    return ordered[index]


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def query_without_pool() -> None:
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(QUERY)
        cur.fetchone()
        cur.close()
    finally:
        conn.close()


def query_with_pool() -> None:
    conn = database.get_db_connection()
    if conn is None:
        raise RuntimeError("pool returned no connection")
    try:
        cur = conn.cursor()
        cur.execute(QUERY)
        cur.fetchone()
        cur.close()
    finally:
        conn.close()


def measure(func) -> Sample:
    start = time.perf_counter()
    try:
        func()
        return Sample(True, (time.perf_counter() - start) * 1000)
    except Exception as exc:
        return Sample(False, (time.perf_counter() - start) * 1000, str(exc))


def run_concurrent(func, label: str) -> list[Sample]:
    print(f"Running {label}: {NUM_SESSIONS} concurrent sessions...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_SESSIONS) as executor:
        futures = [executor.submit(measure, func) for _ in range(NUM_SESSIONS)]
        return [future.result() for future in concurrent.futures.as_completed(futures)]


def summarize(samples: list[Sample]) -> dict[str, float | int | str]:
    ok_latencies = [sample.latency_ms for sample in samples if sample.ok]
    errors = [sample for sample in samples if not sample.ok]
    first_error = errors[0].error if errors else ""
    return {
        "ok": len(ok_latencies),
        "errors": len(errors),
        "avg": avg(ok_latencies),
        "p95": percentile(ok_latencies, 95),
        "error_rate": (len(errors) / len(samples) * 100) if samples else 0.0,
        "first_error": first_error,
    }


def main() -> int:
    print("MANUAL ONLY: benchmark connects to the real MySQL configured in .env.")
    print("Query: SELECT 1")

    # Initialize pool outside the timed section so pooled measurements reflect
    # acquisition/query overhead, not first-time pool construction.
    database._db_pool = None
    warmup = database.get_db_connection()
    if warmup is None:
        print("Cannot initialize pooled DB connection. Check DB_HOST/DB_USER/DB_DATABASE.")
        return 2
    warmup.close()

    pooled = run_concurrent(query_with_pool, "WITH pool_size=15")
    no_pool = run_concurrent(query_without_pool, "WITHOUT pool")

    pooled_summary = summarize(pooled)
    no_pool_summary = summarize(no_pool)

    if pooled_summary["ok"] == 0 or no_pool_summary["ok"] == 0:
        print("\nBenchmark failed: no successful samples in one of the scenarios.")
        print(f"Without pool first error: {no_pool_summary['first_error']}")
        print(f"With pool first error: {pooled_summary['first_error']}")
        return 2

    speedup = no_pool_summary["avg"] / pooled_summary["avg"] if pooled_summary["avg"] else 0.0
    p95_reduction = (
        (1 - pooled_summary["p95"] / no_pool_summary["p95"]) * 100
        if no_pool_summary["p95"]
        else 0.0
    )

    print("\n| Metric                  | Without Pool | With Pool | Improvement |")
    print("|-------------------------|-------------:|----------:|------------:|")
    print(
        f"| Avg request latency     | {no_pool_summary['avg']:>10.1f}ms | "
        f"{pooled_summary['avg']:>7.1f}ms | {speedup:>9.1f}x |"
    )
    print(
        f"| Request P95             | {no_pool_summary['p95']:>10.1f}ms | "
        f"{pooled_summary['p95']:>7.1f}ms | {p95_reduction:>8.1f}% |"
    )
    print(
        f"| Error rate              | {no_pool_summary['error_rate']:>10.1f}% | "
        f"{pooled_summary['error_rate']:>7.1f}% | {'stable':>11} |"
    )
    print(
        f"| Success samples         | {no_pool_summary['ok']:>11} | "
        f"{pooled_summary['ok']:>9} | {NUM_SESSIONS:>11} |"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
