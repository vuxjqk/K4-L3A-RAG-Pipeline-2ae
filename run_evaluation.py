"""Run from repo root: python run_evaluation.py --limit 2 --out smoke_eval.

Ragas 0.4.3; uses existing google-genai and local BGE-M3 dependencies.
No repository files or RESULT.md are overwritten. Resume requires identical
code/data/config; failures remain visible and are never counted as zero.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time
from datetime import datetime, timezone

ROOT = Path.cwd()
METRICS = [
    "faithfulness",
    "answer_relevancy",
    "context_recall",
    "context_precision",
]


def require_repo_root() -> None:
    required = [
        ROOT / "src",
        ROOT / "group_project" / "evaluation" / "golden_dataset.json",
    ]
    if not all(path.exists() for path in required):
        raise RuntimeError(
            "Run this script from the repository root "
            "(the folder containing src/ and group_project/)."
        )


def write_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def fingerprint() -> str:
    digest = hashlib.sha256()
    paths = [ROOT / "group_project" / "evaluation" / "golden_dataset.json"]
    for folder, pattern in [("src", "*.py"), ("data/standardized", "*.md")]:
        paths.extend(sorted((ROOT / folder).rglob(pattern)))
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def validate_score(value, name: str) -> float:
    score = float(value)
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1], got {value!r}")
    return score


def validate_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Judge response must be a JSON object")

    for config_name in ("A", "B"):
        if config_name not in payload:
            raise ValueError(f"Missing config {config_name} in judge response")

        item = payload[config_name]
        if not isinstance(item, dict):
            raise ValueError(f"Config {config_name} must be an object")

        answer = str(item.get("answer", "")).strip()
        if not answer:
            raise ValueError(f"Config {config_name} returned empty answer")

        scores = item.get("scores")
        if not isinstance(scores, dict):
            raise ValueError(f"Config {config_name} missing scores")

        normalized = {}
        for metric in METRICS:
            if metric not in scores:
                raise ValueError(f"Config {config_name} missing metric {metric}")
            normalized[metric] = validate_score(
                scores[metric], f"{config_name}.{metric}"
            )

        item["answer"] = answer
        item["scores"] = normalized
        item["reason"] = str(item.get("reason", "")).strip()

    return payload


def build_pair_prompt(
    question: str,
    reference_answer: str,
    expected_context: str,
    contexts_a: list[str],
    contexts_b: list[str],
) -> str:
    def pack_contexts(contexts: list[str]) -> str:
        if not contexts:
            return "(no retrieved context)"
        parts = []
        for i, context in enumerate(contexts, 1):
            parts.append(f"[Chunk {i}]\n{context}")
        return "\n\n".join(parts)

    return f"""
You are evaluating two RAG retrieval configurations for the SAME user question.

IMPORTANT:
1. Generate answer A using ONLY Context A.
2. Generate answer B using ONLY Context B.
3. Do NOT copy the reference answer into an answer unless it is supported by that config's retrieved context.
4. After generating each answer, score that config using the rubric below.
5. Return STRICT JSON only. No Markdown fences.

QUESTION:
{question}

REFERENCE ANSWER (used only for evaluation, not as evidence):
{reference_answer}

EXPECTED EVIDENCE / EXPECTED CONTEXT:
{expected_context}

CONTEXT A — dense-only:
{pack_contexts(contexts_a)}

CONTEXT B — dense + BM25 + RRF:
{pack_contexts(contexts_b)}

SCORING RUBRIC — each score must be a number from 0.0 to 1.0:

faithfulness:
How strongly the generated answer is supported by that config's retrieved context.
1.0 = all substantive claims supported; 0.0 = unsupported or contradicted.

answer_relevancy:
How directly and completely the generated answer addresses the question.
1.0 = directly answers the question; 0.0 = irrelevant.

context_recall:
How much of the information needed to support the REFERENCE ANSWER is present
in that config's retrieved context.
1.0 = all needed evidence is retrieved; 0.0 = none.

context_precision:
How much of the retrieved context is actually useful/relevant for answering
the question/reference.
1.0 = retrieved chunks are highly focused/relevant; 0.0 = mostly irrelevant.

Return exactly this shape:
{{
  "A": {{
    "answer": "...",
    "scores": {{
      "faithfulness": 0.0,
      "answer_relevancy": 0.0,
      "context_recall": 0.0,
      "context_precision": 0.0
    }},
    "reason": "brief evidence-based explanation"
  }},
  "B": {{
    "answer": "...",
    "scores": {{
      "faithfulness": 0.0,
      "answer_relevancy": 0.0,
      "context_recall": 0.0,
      "context_precision": 0.0
    }},
    "reason": "brief evidence-based explanation"
  }}
}}
""".strip()


def summarize(rows: list[dict], output: Path, manifest: dict) -> None:
    fields = [
        "case_id",
        "config",
        "question",
        "type",
        "judge_seconds",
        "status",
        *METRICS,
    ]
    with (output / "scores.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    lookup = {(r["case_id"], r["config"]): r for r in rows}
    case_ids = sorted({r["case_id"] for r in rows})
    paired = [
        case_id
        for case_id in case_ids
        if all(
            lookup.get((case_id, config_name), {}).get("status") == "scored"
            for config_name in ("A", "B")
        )
    ]

    lines = [
        "# Evaluation summary",
        "",
        f"Started (UTC): {manifest['started_utc']}",
        f"Pair generator/judge model: {manifest['model']}",
        f"Git commit: {manifest['git_commit']}",
        f"Working-tree fingerprint: {manifest['fingerprint']}",
        f"In-domain cases selected: {manifest['selected_count']}",
        f"Complete paired A/B cases: {len(paired)}",
        "",
        "A: dense top-k.",
        "B: dense + BM25 (2*top-k each), RRF k=60, final top-k.",
        "PageIndex disabled in both configs for the A/B comparison.",
        "One Gemini request evaluates BOTH configs for one case to reduce quota usage.",
        "This is LLM-as-judge, NOT Ragas. The same model generates and judges both answers,",
        "which can introduce self-judge/reference leakage bias; this limitation must be reported.",
        "",
        "| Metric | A | B | B-A |",
        "|---|---:|---:|---:|",
    ]

    averages = {"A": [], "B": []}

    for metric in METRICS:
        if paired:
            a = statistics.mean(lookup[(i, "A")][metric] for i in paired)
            b = statistics.mean(lookup[(i, "B")][metric] for i in paired)
            averages["A"].append(a)
            averages["B"].append(b)
            lines.append(f"| {metric} | {a:.4f} | {b:.4f} | {b-a:+.4f} |")
        else:
            lines.append(f"| {metric} | N/A | N/A | N/A |")

    if paired:
        a = statistics.mean(averages["A"])
        b = statistics.mean(averages["B"])
        lines.append(f"| Average | {a:.4f} | {b:.4f} | {b-a:+.4f} |")

    lines.extend(["", "## Lowest-scoring rows"])

    scored = [row for row in rows if row.get("status") == "scored"]
    for row in sorted(
        scored,
        key=lambda r: statistics.mean(r[m] for m in METRICS),
    )[:3]:
        mean_score = statistics.mean(row[m] for m in METRICS)
        lines.append(
            f"- Case {row['case_id']} / {row['config']} / "
            f"mean={mean_score:.4f}: {row['question']}"
        )
        if row.get("reason"):
            lines.append(f"  Reason: {row['reason']}")

    errors = [row for row in rows if row.get("status") != "scored"]
    if errors:
        lines.extend(["", "## Rows needing attention"])
        for row in errors:
            lines.append(
                f"- Case {row['case_id']} / {row['config']}: "
                f"{row.get('status')} {row.get('error', '')}"
            )

    lines.extend(
        [
            "",
            "## Method limitation",
            "",
            "Scores are produced by one LLM-as-judge request per case.",
            "The reference answer and expected evidence are visible to the judge.",
            "The same model generates and judges A/B answers, so scores are useful for",
            "a controlled within-run A/B comparison but should not be presented as",
            "independent human judgment or as Ragas metrics.",
        ]
    )

    (output / "summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    require_repo_root()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=15,
        help="Number of in-domain cases to evaluate. Default: 15.",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--out", default="low_quota_eval")
    parser.add_argument(
        "--model",
        default=os.getenv("PAIR_EVAL_MODEL", "gemini-2.5-flash-lite"),
        help="Gemini model used for pair generation + judging.",
    )
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    if args.limit <= 0:
        parser.error("--limit must be > 0")
    if args.top_k <= 0:
        parser.error("--top-k must be > 0")

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY in .env")

    from google import genai
    from google.genai import types

    from src.task4_chunking_indexing import (
        embed_texts,
        get_collection,
        EMBEDDING_MODEL,
    )
    from src.task5_semantic_search import semantic_search
    import src.task6_lexical_search as lexical
    from src.task7_reranking import rerank_rrf
    from src.task10_generation import reorder_for_llm

    cases = json.loads(
        (
            ROOT
            / "group_project"
            / "evaluation"
            / "golden_dataset.json"
        ).read_text(encoding="utf-8")
    )

    in_domain = [
        (i, case)
        for i, case in enumerate(cases, 1)
        if case.get("type") != "out-of-domain"
    ]
    selected = in_domain[: args.limit]

    if len(selected) < args.limit:
        print(
            f"Requested {args.limit} cases but only {len(selected)} "
            "in-domain cases are available."
        )

    output = ROOT / "group_project" / "evaluation" / args.out
    output.mkdir(parents=True, exist_ok=True)

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()

    config = {
        "fingerprint": fingerprint(),
        "model": args.model,
        "embedding_model": EMBEDDING_MODEL,
        "top_k": args.top_k,
        "limit": args.limit,
        "selected_count": len(selected),
    }

    manifest_path = output / "manifest.json"

    if manifest_path.exists():
        if not args.resume:
            raise RuntimeError(
                "Output already exists. Use --resume or choose a new --out."
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if any(manifest.get(k) != v for k, v in config.items()):
            raise RuntimeError(
                "Code/data/config changed. Use a new --out directory."
            )
    else:
        manifest = {
            **config,
            "git_commit": commit,
            "started_utc": datetime.now(timezone.utc).isoformat(),
        }
        write_json(manifest_path, manifest)

    raw_path = output / "raw.json"
    rows = (
        json.loads(raw_path.read_text(encoding="utf-8"))
        if raw_path.exists()
        else []
    )
    records = {(r["case_id"], r["config"]): r for r in rows}

    if get_collection().count() == 0:
        raise RuntimeError(
            "Chroma is empty. Run python -m src.task4_chunking_indexing first."
        )

    # Warm local components once.
    embed_texts(["warm up"])
    lexical.CORPUS = lexical.get_corpus()
    semantic_search("tuyen sinh", top_k=1)

    client = genai.Client(api_key=api_key)

    for position, (case_id, case) in enumerate(selected, 1):
        existing_a = records.get((case_id, "A"))
        existing_b = records.get((case_id, "B"))

        if (
            existing_a
            and existing_b
            and existing_a.get("status") == "scored"
            and existing_b.get("status") == "scored"
        ):
            print(
                f"[{position}/{len(selected)}] Case {case_id}: already scored",
                flush=True,
            )
            continue

        print(
            f"[{position}/{len(selected)}] Case {case_id}: "
            "retrieve A/B + 1 Gemini request",
            flush=True,
        )

        try:
            chunks_a = semantic_search(
                case["question"],
                top_k=args.top_k,
            )

            dense = semantic_search(
                case["question"],
                top_k=args.top_k * 2,
            )
            sparse = lexical.lexical_search(
                case["question"],
                top_k=args.top_k * 2,
            )
            chunks_b = rerank_rrf(
                [dense, sparse],
                top_k=args.top_k,
                k=60,
            )

            chunks_a = reorder_for_llm(chunks_a)
            chunks_b = reorder_for_llm(chunks_b)

            contexts_a = [chunk["content"] for chunk in chunks_a]
            contexts_b = [chunk["content"] for chunk in chunks_b]

            prompt = build_pair_prompt(
                question=case["question"],
                reference_answer=case["expected_answer"],
                expected_context=case.get("expected_context", ""),
                contexts_a=contexts_a,
                contexts_b=contexts_b,
            )

            start = time.perf_counter()

            response = client.models.generate_content(
                model=args.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )

            judge_seconds = time.perf_counter() - start

            if not response.text:
                raise RuntimeError("Gemini returned empty text")

            payload = json.loads(clean_json_text(response.text))
            payload = validate_payload(payload)

            for config_name, chunks, contexts in (
                ("A", chunks_a, contexts_a),
                ("B", chunks_b, contexts_b),
            ):
                item = payload[config_name]
                row = {
                    "case_id": case_id,
                    "config": config_name,
                    "question": case["question"],
                    "type": case.get("type", "factual"),
                    "reference": case["expected_answer"],
                    "expected_context": case.get("expected_context", ""),
                    "response": item["answer"],
                    "sources": chunks,
                    "retrieved_contexts": contexts,
                    "judge_seconds": judge_seconds,
                    "reason": item["reason"],
                    "status": "scored",
                    **item["scores"],
                }

                previous = records.get((case_id, config_name))
                if previous is None:
                    rows.append(row)
                else:
                    previous.clear()
                    previous.update(row)

                records[(case_id, config_name)] = row

            write_json(raw_path, rows)
            summarize(rows, output, manifest)

        except Exception as error:
            print(f"Paused on error: {error}", flush=True)
            # Preserve a visible error row so it is never silently counted as zero.
            error_row = {
                "case_id": case_id,
                "config": "PAIR",
                "question": case["question"],
                "type": case.get("type", "factual"),
                "status": "error",
                "error": str(error),
            }
            rows.append(error_row)
            write_json(raw_path, rows)
            summarize(rows, output, manifest)
            print(
                "Fix the issue, then rerun the SAME command with --resume.",
                flush=True,
            )
            raise SystemExit(1)

    summarize(rows, output, manifest)
    print(f"Done. See: {output / 'summary.md'}")
    print(f"Raw results: {raw_path}")
    print(f"CSV: {output / 'scores.csv'}")


if __name__ == "__main__":
    main()