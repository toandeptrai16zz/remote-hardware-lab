#!/usr/bin/env python3
"""Manual benchmark for sandbox container lifecycle timings.

This script intentionally talks to the real Docker daemon. It only creates
temporary containers with an `epu_bench_sandbox_` prefix and removes those
containers in the cleanup step.
"""

from __future__ import annotations

import math
import os
import statistics
import subprocess
import time
import uuid


IMAGE_NAME = os.getenv("BENCHMARK_SANDBOX_IMAGE", "my-dev-env:v2")
PULL_IMAGE = os.getenv("BENCHMARK_PULL_IMAGE", "alpine:3.20")
ITERATIONS = int(os.getenv("BENCHMARK_ITERATIONS", "20"))
PREFIX = f"epu_bench_sandbox_{uuid.uuid4().hex[:8]}"


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        capture_output=True,
        text=True,
    )


def timed(cmd: list[str], check: bool = True) -> tuple[float, subprocess.CompletedProcess[str]]:
    start = time.perf_counter()
    result = run_cmd(cmd, check=check)
    return time.perf_counter() - start, result


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil((percent / 100) * len(ordered)) - 1)
    return ordered[index]


def avg(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def image_exists(image: str) -> bool:
    result = run_cmd(["docker", "image", "inspect", image], check=False)
    return result.returncode == 0


def cleanup(names: list[str]) -> None:
    for name in names:
        run_cmd(["docker", "rm", "-f", name], check=False)


def create_sleep_container(name: str) -> None:
    run_cmd(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--entrypoint",
            "sleep",
            IMAGE_NAME,
            "3600",
        ]
    )


def benchmark_running_container(name: str) -> list[float]:
    measurements: list[float] = []
    for _ in range(ITERATIONS):
        start = time.perf_counter()
        run_cmd(["docker", "inspect", name])
        run_cmd(
            [
                "docker",
                "exec",
                name,
                "sh",
                "-lc",
                "service ssh start >/dev/null 2>&1 || true",
            ]
        )
        measurements.append(time.perf_counter() - start)
    return measurements


def benchmark_stopped_container(name: str) -> list[float]:
    measurements: list[float] = []
    for _ in range(ITERATIONS):
        run_cmd(["docker", "stop", "-t", "0", name], check=False)
        duration, _ = timed(["docker", "start", name])
        measurements.append(duration)
    return measurements


def benchmark_new_local(containers: list[str]) -> list[float]:
    measurements: list[float] = []
    for index in range(ITERATIONS):
        name = f"{PREFIX}_new_{index}"
        containers.append(name)
        duration, _ = timed(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "--entrypoint",
                "sleep",
                IMAGE_NAME,
                "3600",
            ]
        )
        measurements.append(duration)
        run_cmd(["docker", "rm", "-f", name], check=False)
    return measurements


def print_row(label: str, values: list[float], note: str) -> None:
    print(
        f"| {label:<34} | {avg(values):>7.3f}s | "
        f"{percentile(values, 95):>7.3f}s | {note:<28} |"
    )


def main() -> int:
    print("MANUAL ONLY: benchmark talks to the real Docker daemon.")
    print(f"Sandbox image: {IMAGE_NAME}")
    print(f"Iterations: {ITERATIONS}")
    print(f"Temp prefix: {PREFIX}")

    containers: list[str] = []
    base = f"{PREFIX}_base"
    containers.append(base)

    try:
        if not image_exists(IMAGE_NAME):
            print(f"Missing sandbox image: {IMAGE_NAME}")
            return 2

        cleanup(containers)
        create_sleep_container(base)

        running = benchmark_running_container(base)
        stopped = benchmark_stopped_container(base)
        local_new = benchmark_new_local(containers)

        pull_note = "already cached"
        pull_values: list[float] = []
        if not image_exists(PULL_IMAGE):
            duration, result = timed(["docker", "pull", PULL_IMAGE], check=False)
            pull_values.append(duration)
            pull_note = "pulled via Internet" if result.returncode == 0 else "pull failed"

        print("\n| Scenario                           |      Avg |      P95 | Note                         |")
        print("|------------------------------------|---------:|---------:|------------------------------|")
        print_row("Existing container, running", running, "inspect + ssh check")
        print_row("Existing container, stopped", stopped, "docker start")
        print_row("New container, local image", local_new, "docker run local cache")
        if pull_values:
            print(
                f"| Missing image pull                 | {pull_values[0]:>7.3f}s | "
                f"{'-':>8} | {pull_note:<28} |"
            )
        else:
            print(f"| Missing image pull                 | {'-':>8} | {'-':>8} | {pull_note:<28} |")

        return 0
    finally:
        cleanup(containers)


if __name__ == "__main__":
    raise SystemExit(main())
