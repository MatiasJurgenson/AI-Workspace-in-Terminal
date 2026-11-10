#!/usr/bin/env python3
"""
Run X-PLUG/WritingBench prompts through the official Goose CLI.

Expected input JSONL records:
    {"index": 0, "query": "..."}

Output JSONL records (compatible with WritingBench):
    {"index": 0, "response": "..."}

Features:
- Uses `goose run` in non-interactive mode and sends prompts over stdin.
- Resumes safely by index (not merely by line count).
- Writes each successful result immediately.
- Retries failed CLI calls and records failures separately.
- Supports task limits, timeouts, model/provider overrides and a working directory.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{line_no}: each JSONL record must be an object")
            if "index" not in item:
                raise ValueError(f"{path}:{line_no}: missing required 'index'")
            if not isinstance(item.get("query"), str) or not item["query"].strip():
                raise ValueError(f"{path}:{line_no}: missing/empty string 'query'")
            records.append(item)
    return records


def read_completed(path: Path) -> dict[Any, dict[str, Any]]:
    completed: dict[Any, dict[str, Any]] = {}
    if not path.exists():
        return completed
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_no}: invalid JSON. Fix/remove the damaged line before resuming."
                ) from exc
            if "index" in item and isinstance(item.get("response"), str):
                completed[item["index"]] = item
    return completed


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def build_command(args: argparse.Namespace) -> list[str]:
    cmd = [
        args.goose_bin,
        "run",
        "--no-session",
        "--instructions",
        "-",
        "--quiet",
        "--output-format",
        "text",
    ]
    if args.provider:
        cmd += ["--provider", args.provider]
    if args.model:
        cmd += ["--model", args.model]
    if args.max_turns is not None:
        cmd += ["--max-turns", str(args.max_turns)]
    if args.system:
        cmd += ["--system", args.system]
    return cmd


def run_one(
    command: list[str],
    prompt: str,
    cwd: Path,
    timeout: int,
    env: dict[str, str],
) -> str:
    result = subprocess.run(
        command,
        input=prompt,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        cwd=str(cwd),
        env=env,
        timeout=timeout,
        check=False,
    )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if result.returncode != 0:
        detail = stderr or stdout or "(Goose returned no diagnostic output)"
        raise RuntimeError(f"Goose exited with status {result.returncode}: {detail[-5000:]}")
    if not stdout:
        raise RuntimeError(
            "Goose exited successfully but produced empty stdout. "
            f"stderr: {stderr[-2000:] or '(empty)'}"
        )
    return stdout


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate WritingBench responses using the local Goose CLI."
    )
    parser.add_argument("--query-file", required=True, type=Path,
                        help="WritingBench JSONL file containing index and query fields.")
    parser.add_argument("--output-file", required=True, type=Path,
                        help="Response JSONL output (index and response fields).")
    parser.add_argument("--goose-bin", default="goose",
                        help="Goose executable name or full path (default: goose).")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(),
                        help="Working directory for Goose (default: current directory).")
    parser.add_argument("--limit", type=int, default=0,
                        help="Maximum number of input tasks to process; 0 means all.")
    parser.add_argument("--timeout", type=int, default=1800,
                        help="Per-task timeout in seconds (default: 1800).")
    parser.add_argument("--retries", type=int, default=2,
                        help="Retries after the first attempt (default: 2).")
    parser.add_argument("--retry-delay", type=float, default=3.0,
                        help="Seconds between retries.")
    parser.add_argument("--sleep", type=float, default=0.0,
                        help="Seconds to wait between successful tasks.")
    parser.add_argument("--provider", default=None, help="Optional Goose provider override.")
    parser.add_argument("--model", default=None, help="Optional Goose model override.")
    parser.add_argument("--max-turns", type=int, default=None,
                        help="Optional Goose agent-turn limit.")
    parser.add_argument("--system", default=None,
                        help="Optional additional system instruction for Goose.")
    parser.add_argument("--force", action="store_true",
                        help="Ignore existing output and start a fresh output file.")
    args = parser.parse_args()

    if args.limit < 0 or args.retries < 0 or args.timeout <= 0:
        parser.error("--limit and --retries must be >= 0; --timeout must be > 0")
    if not args.cwd.exists() or not args.cwd.is_dir():
        parser.error(f"Goose working directory does not exist: {args.cwd}")
    executable = shutil.which(args.goose_bin)
    if executable is None:
        parser.error(
            f"Cannot find Goose executable '{args.goose_bin}'. "
            "Install Goose and ensure it is on PATH, or pass --goose-bin."
        )
    args.goose_bin = executable

    tasks = read_jsonl(args.query_file)
    if args.limit:
        tasks = tasks[:args.limit]
    args.output_file.parent.mkdir(parents=True, exist_ok=True)

    if args.force and args.output_file.exists():
        args.output_file.unlink()
    completed = read_completed(args.output_file)

    errors_file = args.output_file.with_suffix(args.output_file.suffix + ".errors.jsonl")
    command = build_command(args)
    env = os.environ.copy()

    print(f"Input tasks: {len(tasks)}")
    print(f"Already completed: {len(completed)}")
    print(f"Goose command: {' '.join(command[:-1]) if args.system else ' '.join(command)}")
    print(f"Working directory: {args.cwd.resolve()}")
    print(f"Output: {args.output_file.resolve()}")

    successes = 0
    failures = 0
    for position, task in enumerate(tasks, 1):
        idx = task["index"]
        if idx in completed:
            print(f"[{position}/{len(tasks)}] index={idx}: already done; skipping")
            continue

        prompt = task["query"]
        print(f"[{position}/{len(tasks)}] index={idx}: running Goose...", flush=True)
        last_error = None
        for attempt in range(args.retries + 1):
            try:
                response = run_one(
                    command=command,
                    prompt=prompt,
                    cwd=args.cwd,
                    timeout=args.timeout,
                    env=env,
                )
                append_jsonl(args.output_file, {"index": idx, "response": response})
                successes += 1
                print(f"  saved ({len(response)} characters)")
                last_error = None
                break
            except subprocess.TimeoutExpired:
                last_error = f"Timed out after {args.timeout} seconds"
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"

            if attempt < args.retries:
                print(f"  attempt {attempt + 1} failed: {last_error}; retrying...")
                time.sleep(args.retry_delay)

        if last_error is not None:
            failures += 1
            append_jsonl(errors_file, {
                "index": idx,
                "error": last_error,
                "query": prompt,
            })
            print(f"  FAILED: {last_error}", file=sys.stderr)

        if args.sleep:
            time.sleep(args.sleep)

    print("\nFinished.")
    print(f"New successful responses: {successes}")
    print(f"Failed tasks: {failures}")
    print(f"Response file: {args.output_file}")
    if failures:
        print(f"Failure log: {errors_file}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
