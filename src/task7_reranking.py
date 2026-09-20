"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.

-> Dùng Jina hoặc self host hoặc bất cứ công cụ nào bạn quen
"""


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult."""
    if top_k <= 0:
        return []

    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    for ranked_list in ranked_lists:
        seen: set[str] = set()  # mỗi list chỉ tính một lần cho mỗi id
        rank = 0
        for item in ranked_list:
            item_id = item["id"]
            if item_id in seen:
                continue
            seen.add(item_id)
            rank += 1  # rank bắt đầu từ 1
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            items.setdefault(item_id, item)

    # sorted ổn định: id hòa điểm giữ thứ tự xuất hiện đầu tiên
    ranked_ids = sorted(scores, key=scores.get, reverse=True)
    results = []
    for item_id in ranked_ids[:top_k]:
        result = items[item_id].copy()
        result["metadata"] = dict(result.get("metadata") or {})
        result["score"] = scores[item_id]
        result["retrieval_method"] = "hybrid"
        results.append(result)
    return results


if __name__ == "__main__":
    print("Implement rerank_rrf, then run contract tests.")
