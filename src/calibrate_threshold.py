"""
Calibrate SCORE_THRESHOLD cho fallback của Task 9.

So sánh best dense cosine score của query in-domain (golden dataset) với query
out-of-domain, rồi gợi ý ngưỡng tách tốt nhất giữa hai nhóm.

    python -m src.calibrate_threshold
"""

import json
from pathlib import Path

from .task5_semantic_search import semantic_search


GOLDEN_PATH = (
    Path(__file__).parent.parent / "group_project" / "evaluation" / "golden_dataset.json"
)

# Query ngoài domain bổ sung (golden dataset chỉ có vài câu).
EXTRA_OUT_OF_DOMAIN = [
    "Cách nấu phở bò Hà Nội ngon nhất?",
    "Tỷ giá USD hôm nay là bao nhiêu?",
    "Ai vô địch World Cup 2018?",
    "Hướng dẫn cài đặt Windows 11 từ USB",
    "Học phí Đại học Kinh tế Quốc dân là bao nhiêu?",
    "Điểm chuẩn Đại học Y Hà Nội năm 2024?",
    "Lịch thi đấu Ngoại hạng Anh cuối tuần này",
    "Thời tiết Đà Nẵng ngày mai thế nào?",
]


def best_dense_score(query: str) -> float:
    results = semantic_search(query, top_k=5)
    return results[0]["score"] if results else 0.0


def suggest_threshold(in_scores: list[float], out_scores: list[float]) -> tuple[float, float]:
    """Chọn ngưỡng t (in-domain nếu score >= t) tối đa balanced accuracy."""
    candidates = sorted(set(in_scores + out_scores))
    best_t, best_acc = 0.0, -1.0
    for t in candidates:
        tpr = sum(s >= t for s in in_scores) / len(in_scores)
        tnr = sum(s < t for s in out_scores) / len(out_scores)
        acc = (tpr + tnr) / 2
        if acc > best_acc:
            best_t, best_acc = t, acc
    return best_t, best_acc


def main() -> None:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    in_domain = [c["question"] for c in golden if c.get("type") != "out-of-domain"]
    out_domain = [c["question"] for c in golden if c.get("type") == "out-of-domain"]
    out_domain += EXTRA_OUT_OF_DOMAIN

    in_scores = [best_dense_score(q) for q in in_domain]
    out_scores = [best_dense_score(q) for q in out_domain]

    print(f"In-domain     n={len(in_scores)}  min={min(in_scores):.3f}  "
          f"mean={sum(in_scores)/len(in_scores):.3f}  max={max(in_scores):.3f}")
    print(f"Out-of-domain n={len(out_scores)}  min={min(out_scores):.3f}  "
          f"mean={sum(out_scores)/len(out_scores):.3f}  max={max(out_scores):.3f}")

    print("\nOut-of-domain (score cao nhất trước):")
    for score, query in sorted(zip(out_scores, out_domain), reverse=True):
        print(f"  {score:.3f}  {query}")
    print("\nIn-domain (score thấp nhất trước):")
    for score, query in sorted(zip(in_scores, in_domain))[:5]:
        print(f"  {score:.3f}  {query}")

    threshold, accuracy = suggest_threshold(in_scores, out_scores)
    print(f"\nGợi ý SCORE_THRESHOLD={threshold:.2f} (balanced accuracy {accuracy:.2f})")
    if min(in_scores) <= max(out_scores):
        print("Lưu ý: hai nhóm chồng lấn nhau, dense score một mình không tách hết được; "
              "cần safe refusal ở bước generation.")


if __name__ == "__main__":
    main()
