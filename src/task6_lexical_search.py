"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""


CORPUS: list[dict] = []


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""

    from rank_bm25 import BM25Okapi

    # Biến content của từng chunk thành list các từ
    tokenized_corpus = [
        item["content"].lower().split()
        for item in corpus
    ]

    return BM25Okapi(tokenized_corpus)


def get_corpus() -> list[dict]:
    """
    Lấy corpus chunks.

    - Nếu CORPUS đã có dữ liệu thì dùng luôn.
      Điều này cũng giúp unit test có thể monkeypatch CORPUS.
    - Nếu CORPUS đang rỗng thì load và chunk dữ liệu từ Task 4.
    """

    if CORPUS:
        return CORPUS

    from .task4_chunking_indexing import (
        load_documents,
        chunk_documents,
    )

    documents = load_documents()
    return chunk_documents(documents)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""

    corpus = get_corpus()

    if not corpus:
        return []

    bm25 = build_bm25_index(corpus)

    query_tokens = query.lower().split()
    scores = bm25.get_scores(query_tokens)

    ranked_indices = sorted(
        range(len(corpus)),
        key=lambda i: (
            float(scores[i]),
            len(
                set(query_tokens)
                & set(corpus[i]["content"].lower().split())
            ),
        ),
        reverse=True,
    )

    results = []

    for index in ranked_indices:
        item = corpus[index]

        content_tokens = set(
            item["content"].lower().split()
        )

        overlap = set(query_tokens) & content_tokens

        if not overlap:
            continue

        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": float(scores[index]),
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })

        if len(results) >= top_k:
            break

    return results


if __name__ == "__main__":
    for result in lexical_search(
        "phương thức tuyển sinh",
        top_k=3
    ):
        print(result)