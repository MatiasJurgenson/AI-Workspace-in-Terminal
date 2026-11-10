Run benchmark

```
python benchmark.py   --query-file benchmark_query/benchmark_all.jsonl   --output-file responses_l_14/goose.jsonl --limit 50
python evaluate_benchmark.py   --evaluator critic   --query_criteria_file benchmark_query/benchmark_all.jsonl   --input_file responses_l_14/goose.jsonl   --output_file score_dir_l_14/goose.jsonl
python calculate_scores.py   --score_dir ./score_dir_l_14/   --benchmark_file ./benchmark_query/benchmark_all.jsonl   --output_excel ./scores_l_14.xlsx   --requirement_dir ./benchmark_query/requirement
```