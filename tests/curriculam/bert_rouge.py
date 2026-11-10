### SETUP

# python -m venv .venv
# source .venv/bin/activate 
# pip install bert-score rouge-score pandas numpy torch


import re
import pandas as pd
from pathlib import Path
from bert_score import score
from rouge_score import rouge_scorer

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results_o_7" # change this to the folder where your generated lessons are stored 

# ==========================================
# CONFIGURATION
# ==========================================

NUM_LESSONS = 50  # Change this to 5, 10, 50, 100, or 647

index = ROOT / "LessonBench" / "LessonBench-V1.csv"
df_index = pd.read_csv(index).head(NUM_LESSONS)

# ==========================================
# TEXT LOADING
# ==========================================

def clean_text(path):
    text = Path(path).read_text(encoding="utf-8")
    text = re.sub(r"```(?:markdown)?", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ==========================================
# MATCH GENERATED LESSONS TO REFERENCES
# ==========================================

records = []

for _, row in df_index.iterrows():

    lesson_id = str(row["lesson_id"])
    topic_id = str(row["topic_id"])

    generated = RESULTS / f"{lesson_id}.md"

    reference = (
        ROOT / "LessonBench" / "data" /
        topic_id / lesson_id / "cleaned" / "lesson.md"
    )

    if not generated.exists():
        print(f"Missing generated lesson: {lesson_id}")
        continue

    if not reference.exists():
        print(f"Missing reference lesson: {lesson_id}")
        continue

    records.append({
        "lesson_id": lesson_id,
        "topic_id": topic_id,
        "generated": clean_text(generated),
        "reference": clean_text(reference),
    })


if not records:
    raise RuntimeError("No matching generated/reference lessons found.")

df = pd.DataFrame(records)

print(f"Evaluating {len(df)} lessons...")


# ==========================================
# BERTSCORE
# ==========================================

P, R, F1 = score(
    df["generated"].tolist(),
    df["reference"].tolist(),
    lang="en",
    verbose=True,
    batch_size=4,
    device="cpu"
)

df["bert_precision"] = P.tolist()
df["bert_recall"] = R.tolist()
df["bert_f1"] = F1.tolist()


# ==========================================
# ROUGE-L
# ==========================================

scorer = rouge_scorer.RougeScorer(
    ["rougeL"],
    use_stemmer=True
)

df["rouge_l_f1"] = [
    scorer.score(ref, gen)["rougeL"].fmeasure
    for ref, gen in zip(
        df["reference"], df["generated"]
    )
]


# ==========================================
# SAVE RESULTS
# ==========================================

output_file = RESULTS / "text_metrics.csv"

df.drop(columns=["generated", "reference"]).to_csv(
    output_file,
    index=False
)

print("\n========== BENCHMARK RESULTS ==========")

print(f"Lessons evaluated: {len(df)}")
print(f"Average BERTScore F1: {df['bert_f1'].mean():.4f}")
print(f"Average ROUGE-L F1: {df['rouge_l_f1'].mean():.4f}")

print("\nResults saved to:", output_file)
