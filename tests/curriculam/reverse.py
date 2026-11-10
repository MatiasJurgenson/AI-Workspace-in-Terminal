
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

RESULTS = ROOT / "results_o_7" # change this to the folder where your generated lessons are stored
RECONSTRUCTED = RESULTS / "reconstructed"
PROMPT_FILE = ROOT / "prompts" / "LessonPlan_Creation_prompt.md"

RECONSTRUCTED.mkdir(parents=True, exist_ok=True)

system_prompt = PROMPT_FILE.read_text(encoding="utf-8")

for generated in RESULTS.glob("lesson_*.md"):

    lesson_id = generated.stem
    output = RECONSTRUCTED / f"{lesson_id}.md"

    if output.exists():
        print(f"Already processed: {lesson_id}")
        continue

    lesson = generated.read_text(encoding="utf-8")

    task = f"""
{system_prompt}

The following is the generated lesson to reverse-engineer.

IMPORTANT:
Do not use any original reference lesson or reference lesson plan.
Use only the lesson content below.

{lesson}
"""

    result = subprocess.run(
        [
            "goose", "run",
            "--no-session",
            "--output-format", "text",
            "-t", task,
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode == 0 and result.stdout.strip():
        output.write_text(result.stdout, encoding="utf-8")
        print(f"Completed: {lesson_id}")
    else:
        print(f"Failed: {lesson_id}")
        print(result.stderr[-1000:])
