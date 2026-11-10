import csv
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "LessonBench" / "data"
OUT = ROOT / "results_l_14"
OUT.mkdir(exist_ok=True)

# Use the first 50 rows initially.
# Change this to the CSV filename if necessary.
import pandas as pd

index = ROOT / "LessonBench" / "LessonBench-V1.csv"
df = pd.read_csv(index).head(50)

with (OUT / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f, fieldnames=["lesson_id", "topic", "status", "output"]
    )
    writer.writeheader()

    for _, row in df.iterrows():
        lesson_id = row["lesson_id"]
        topic_id = row["topic_id"]

        folder = DATA / topic_id / lesson_id
        plan = folder / "lesson_plan" / "lesson_plan.md"
        reference = folder / "cleaned" / "lesson.md"
        output = OUT / f"{lesson_id}.md"

        if not plan.exists() or not reference.exists():
            print(f"Skipping missing data: {lesson_id}")
            writer.writerow({
                "lesson_id": lesson_id,
                "topic": row["topic"],
                "status": "missing_data",
                "output": "",
            })
            continue

        prompt = (
            "Generate a complete, accurate STEM lesson using the "
            "lesson plan below. Include learning objectives, explanations, "
            "worked examples, exercises, and assessment. "
            "Do not search for or read any reference lesson. "
            "Return only the lesson content.\n\n"
            + plan.read_text(encoding="utf-8")
        )

        result = subprocess.run(
            [
                "goose", "run",
                "--no-session",
                "--output-format", "text",
                "-t", prompt,
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )

        status = "ok" if result.returncode == 0 else "error"
        if status == "ok" and result.stdout.strip():
            output.write_text(result.stdout, encoding="utf-8")
        else:
            status = "error"
            print(f"{lesson_id}: {result.stderr[-1000:]}")

        writer.writerow({
            "lesson_id": lesson_id,
            "topic": row["topic"],
            "status": status,
            "output": str(output) if status == "ok" else "",
        })
        f.flush()
        print(f"{lesson_id}: {status}")