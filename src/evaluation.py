"""
Evaluation: 4 metric + A/B (dense-only vs hybrid + RRF) trên golden dataset.

    python -m src.evaluation            # chạy cả hai config
    python -m src.evaluation --limit 5  # chạy thử vài câu

Metric:
    - Context recall / precision: tính xác định (không dùng LLM) bằng độ phủ token
      của `expected_context` trong các chunk được retrieve. Chỉ áp dụng cho câu
      in-domain; câu out-of-domain không có context kỳ vọng.
    - Faithfulness / answer relevance: LLM-as-judge (dùng provider trong .env).

Hai config dùng chung golden dataset, generator, prompt, top_k, threshold; chỉ
khác retrieval (`use_reranking`). Kết quả lưu ở group_project/evaluation/results.json.
"""

import argparse
import json
import re
import time
import unicodedata
from pathlib import Path

from .task9_retrieval_pipeline import SCORE_THRESHOLD, retrieve
from .task10_generation import (
    LLM_MODEL,
    SAFE_REFUSAL,
    SYSTEM_PROMPT,
    call_llm,
    format_context,
    reorder_for_llm,
)


EVAL_DIR = Path(__file__).parent.parent / "group_project" / "evaluation"
GOLDEN_PATH = EVAL_DIR / "golden_dataset.json"
RESULTS_PATH = EVAL_DIR / "results.json"

TOP_K = 5
COVERAGE_THRESHOLD = 0.8  # chunk "chứa" snippet nếu phủ >= 80% token của snippet
CONFIGS = {
    "A_dense_only": {"use_reranking": False},
    "B_hybrid_rrf": {"use_reranking": True},
}
METRICS = ("faithfulness", "answer_relevance", "context_recall", "context_precision")

FAITHFULNESS_PROMPT = """Bạn là giám khảo đánh giá tính trung thực (faithfulness) của câu trả lời RAG.
Tách câu trả lời thành các mệnh đề thông tin, rồi đếm bao nhiêu mệnh đề được suy ra trực tiếp từ Context.
Nếu câu trả lời chỉ là lời từ chối (không thể xác minh thông tin) thì coi là hoàn toàn trung thực.
Chỉ trả về JSON: {"total_claims": <số nguyên>, "supported_claims": <số nguyên>}"""

RELEVANCE_PROMPT = """Bạn là giám khảo đánh giá mức độ đúng và liên quan của câu trả lời.
So sánh Answer với Expected answer cho Question.
Điểm: 1.0 = đúng đầy đủ các thông tin chính; 0.5 = đúng một phần hoặc thiếu ý;
0.0 = sai, lạc đề, hoặc từ chối trong khi lẽ ra phải trả lời.
Nếu Expected answer yêu cầu hệ thống từ chối thì lời từ chối/không xác minh được = 1.0,
còn trả lời bằng thông tin cụ thể = 0.0.
Chỉ trả về JSON: {"score": <số từ 0 đến 1>}"""


# ---------------------------------------------------------------- helpers

def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower()


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", _norm(text)))


def _coverage(snippet: str, chunk: str) -> float:
    snippet_tokens = _tokens(snippet)
    if not snippet_tokens:
        return 0.0
    return len(snippet_tokens & _tokens(chunk)) / len(snippet_tokens)


def _snippets(case: dict) -> list[str]:
    if case.get("type") == "out-of-domain":
        return []
    return [s for s in case["expected_context"].split("\n...\n") if s.strip()]


def context_recall(case: dict, chunks: list[dict]) -> float | None:
    """Tỉ lệ snippet kỳ vọng được phủ bởi ít nhất một chunk."""
    snippets = _snippets(case)
    if not snippets:
        return None
    hits = sum(
        any(_coverage(s, c["content"]) >= COVERAGE_THRESHOLD for c in chunks)
        for s in snippets
    )
    return hits / len(snippets)


def context_precision(case: dict, chunks: list[dict]) -> float | None:
    """Average precision theo rank: chunk relevant nếu phủ >= ngưỡng một snippet."""
    snippets = _snippets(case)
    if not snippets:
        return None
    relevant_so_far, total = 0, 0.0
    for rank, chunk in enumerate(chunks, 1):
        if any(_coverage(s, chunk["content"]) >= COVERAGE_THRESHOLD for s in snippets):
            relevant_so_far += 1
            total += relevant_so_far / rank
    return total / relevant_so_far if relevant_so_far else 0.0


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"judge did not return JSON: {text[:100]!r}")
    return json.loads(match.group(0))


def _llm(system_prompt: str, user_message: str, retries: int = 5) -> str:
    """Gọi LLM với retry/backoff (rate limit, lỗi tạm thời)."""
    for attempt in range(retries):
        try:
            return call_llm(system_prompt, user_message)
        except Exception as error:
            if attempt == retries - 1:
                raise
            wait = 5 * 2 ** attempt
            print(f"  LLM error ({error!s:.80}); retry in {wait}s")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def _is_refusal(answer: str) -> bool:
    return SAFE_REFUSAL.lower() in answer.lower()


def generate_answer(query: str, chunks: list[dict]) -> str:
    """Sinh câu trả lời từ chunks đã retrieve, cùng prompt với Task 10."""
    if not chunks:
        return SAFE_REFUSAL
    context = format_context(reorder_for_llm(chunks))
    try:
        answer = _llm(SYSTEM_PROMPT, f"Context:\n{context}\n\nQuestion:\n{query}")
    except Exception as error:
        print(f"  generation failed: {error!s:.100}")
        return SAFE_REFUSAL
    return answer if answer.strip() else SAFE_REFUSAL


def judge_faithfulness(answer: str, chunks: list[dict]) -> float:
    if _is_refusal(answer):
        return 1.0
    verdict = _parse_json(
        _llm(FAITHFULNESS_PROMPT, f"Context:\n{format_context(chunks)}\n\nAnswer:\n{answer}")
    )
    total = int(verdict.get("total_claims", 0))
    return min(1.0, int(verdict.get("supported_claims", 0)) / total) if total else 0.0


def judge_relevance(case: dict, answer: str) -> float:
    verdict = _parse_json(
        _llm(
            RELEVANCE_PROMPT,
            f"Question: {case['question']}\nExpected answer: {case['expected_answer']}\nAnswer: {answer}",
        )
    )
    return max(0.0, min(1.0, float(verdict.get("score", 0.0))))


# ------------------------------------------------------------------- run

def evaluate_case(case: dict, use_reranking: bool) -> dict:
    chunks = retrieve(
        case["question"],
        top_k=TOP_K,
        score_threshold=SCORE_THRESHOLD,
        use_reranking=use_reranking,
    )
    answer = generate_answer(case["question"], chunks)
    recall = context_recall(case, chunks)
    precision = context_precision(case, chunks)
    return {
        "question": case["question"],
        "type": case.get("type", "factual"),
        "answer": answer,
        "retrieved_ids": [c["id"] for c in chunks],
        "retrieval_method": chunks[0]["retrieval_method"] if chunks else "none",
        "faithfulness": judge_faithfulness(answer, chunks),
        "answer_relevance": judge_relevance(case, answer),
        "context_recall": recall,
        "context_precision": precision,
    }


def _mean(values: list[float | None]) -> float | None:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def summarize(rows: list[dict]) -> dict:
    return {m: _mean([r[m] for r in rows]) for m in METRICS}


def failure_stage(row: dict) -> str:
    if row["context_recall"] is not None and row["context_recall"] < 1:
        return "retrieval"
    if row["faithfulness"] < 0.8:
        return "generation (faithfulness)"
    if row["answer_relevance"] < 0.8:
        return "generation (relevance)"
    return "ok"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def print_report(results: dict) -> None:
    names = list(results)
    print("\n## Overall scores\n")
    print("| Metric | " + " | ".join(names) + " |")
    print("| --- | " + " | ".join("---:" for _ in names) + " |")
    for metric in METRICS:
        print(f"| {metric} | " + " | ".join(_fmt(results[n]["summary"][metric]) for n in names) + " |")

    print("\n## Worst performers (5 câu thấp nhất theo từng config)\n")
    print("| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage |")
    print("| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |")
    for name in names:
        ranked = sorted(
            results[name]["cases"],
            key=lambda r: _mean([r[m] for m in METRICS]) or 0.0,
        )[:5]
        for i, r in enumerate(ranked, 1):
            print(
                f"| {i} | {r['question']} | {name} | {_fmt(r['faithfulness'])} | "
                f"{_fmt(r['answer_relevance'])} | {_fmt(r['context_recall'])} | "
                f"{_fmt(r['context_precision'])} | {failure_stage(r)} |"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="chỉ chạy N câu đầu")
    args = parser.parse_args()

    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    if args.limit:
        golden = golden[: args.limit]

    results = {}
    for name, config in CONFIGS.items():
        print(f"\n=== {name} ({len(golden)} cases) ===")
        rows = []
        for i, case in enumerate(golden, 1):
            print(f"[{i}/{len(golden)}] {case['question'][:70]}")
            rows.append(evaluate_case(case, **config))
        results[name] = {"summary": summarize(rows), "cases": rows}

    RESULTS_PATH.write_text(
        json.dumps(
            {
                "meta": {
                    "llm_model": LLM_MODEL,
                    "top_k": TOP_K,
                    "score_threshold": SCORE_THRESHOLD,
                    "golden_size": len(golden),
                    "configs": CONFIGS,
                },
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nSaved: {RESULTS_PATH}")
    print_report(results)


if __name__ == "__main__":
    main()
