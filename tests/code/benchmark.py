
#!/usr/bin/env python3

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

from datasets import load_dataset

import os

MODEL = os.getenv(
    "OPENCODE_MODEL",
    "ollama/qwen3-coder:30b"
)


DATASET = "cabbage972/GitChameleon-2.0"
CONFIG = "problems"


def make_prompt(task):
    docs = task.get("docs") or []
    dependencies = task.get("additional_dependencies") or ""

    return f"""
You are completing a Python coding benchmark.

Your task is to implement the requested code correctly for the
EXACT library and Python versions specified below.

IMPORTANT CONSTRAINTS:
- Do not use APIs introduced after the specified library version.
- Do not assume the latest library version is installed.
- Do not change the requested function or class interface.
- Preserve compatibility with the specified Python version.
- Do not use APIs from newer versions just because you know them.
- Use additional dependencies only when appropriate.
- Do not copy or guess the reference solution.

LIBRARY: {task['library']}
LIBRARY VERSION: {task['version']}
PYTHON VERSION: {task['python_version']}
ADDITIONAL DEPENDENCIES: {dependencies}

PROBLEM:
{task['problem']}

STARTING CODE:
{task['starting_code']}

REFERENCE DOCUMENTATION:
{chr(10).join(docs)}

INSTRUCTIONS:
1. Implement the requested Python code.
2. You MUST create answer.txt in the current working directory.
3. Use your file-writing tool to create the file.
4. The file must contain the complete Python implementation.
5. Do not put Markdown fences in the file.
6. Do not put explanations or comments outside the implementation.
7. Do not merely describe the implementation.
8. Verify that answer.txt exists after writing it.
9. Do not modify any benchmark files.
10. Your final response should simply say DONE.

The evaluator will execute your implementation against hidden tests.
"""


def run_task(task, model, work_root, timeout):
    task_id = str(task["example_id"])
    task_dir = work_root / f"task_{task_id}"

    task_dir.mkdir(parents=True, exist_ok=True)

    answer_file = task_dir / "answer.txt"

    if answer_file.exists():
        answer_file.unlink()

    prompt = make_prompt(task)

    (task_dir / "task.md").write_text(
        prompt, encoding="utf-8"
    )

    command = [
        "opencode",
        "run",
        "--model",
        model,
        "--auto",
        "--dir",
        str(task_dir),
        prompt,
    ]

    print(
        f"\n[{task_id}] "
        f"{task['library']}=={task['version']}"
        f" (Python {task['python_version']})"
    )

    try:
        result = subprocess.run(
            command,
            cwd=task_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            print(f"OpenCode failed: {result.stderr[-1500:]}")
            return ""

        if not answer_file.exists():
            print("WARNING: OpenCode did not create answer.txt")
            print(result.stdout[-1000:])
            return ""

        answer = answer_file.read_text(
            encoding="utf-8"
        ).strip()

        if not answer:
            print("WARNING: Empty answer")
            return ""

        print(f"Generated {len(answer)} characters")
        return answer

    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after {timeout} seconds")
        return ""

    except Exception as exc:
        print(f"ERROR: {exc}")
        return ""


def main():
    parser = argparse.ArgumentParser(
        description="GitChameleon + OpenCode benchmark runner"
    )

    parser.add_argument(
        "--model",
        default=MODEL,
        help="OpenCode model ID",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=30,
        help="Number of tasks to run",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random selection seed",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=1200,
        help="Maximum seconds per task",
    )

    parser.add_argument(
        "--output",
        default="solutions.jsonl",
    )

    parser.add_argument(
        "--workdir",
        default="benchmark_runner/workspaces",
    )

    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count must be positive")

    if args.timeout < 1:
        parser.error("--timeout must be positive")

    if subprocess.run(
        ["opencode", "--version"],
        capture_output=True,
    ).returncode != 0:
        sys.exit("OpenCode CLI is not available")

    print("Loading GitChameleon dataset...")

    dataset = load_dataset(
        DATASET,
        CONFIG,
        split="train",
    )

    if args.count > len(dataset):
        parser.error(
            f"Requested {args.count} tasks, "
            f"but dataset contains {len(dataset)}"
        )

    tasks = list(dataset)

    random.Random(args.seed).shuffle(tasks)
    selected = tasks[:args.count]

    work_root = Path(args.workdir).resolve()
    work_root.mkdir(parents=True, exist_ok=True)

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    results = []

    for index, task in enumerate(selected, 1):
        print(f"\nTask {index}/{len(selected)}")

        answer = run_task(
            task,
            args.model,
            work_root,
            args.timeout,
        )

        results.append({
            "example_id": str(task["example_id"]),
            "answer": answer,
        })

        # Persist after every task so interrupted runs
        # do not lose completed work.
        with output.open("w", encoding="utf-8") as f:
            for item in results:
                f.write(json.dumps(item) + "\n")

    successful = sum(
        bool(item["answer"]) for item in results
    )

    failed = len(results) - successful

    print("\n" + "=" * 50)
    print("GENERATION COMPLETE")
    print("=" * 50)
    print(f"Tasks selected: {len(results)}")
    print(f"Answers generated: {successful}")
    print(f"Generation failures: {failed}")
    print(f"Output: {output}")
    print("=" * 50)

    if failed:
        print(
            "Empty answers are retained in JSONL so "
            "generation failures are not excluded."
        )


if __name__ == "__main__":
    main()
