"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

import unicodedata
from pathlib import Path

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer


STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

# Cache model để không load lại mỗi lần gọi embed_texts().
_model: SentenceTransformer | None = None


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed một danh sách text bằng SentenceTransformer (local, miễn phí)."""
    global _model
    if not texts:
        return []
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    vectors = _model.encode(
        texts,
        normalize_embeddings=True,  # cosine distance cần vector đã chuẩn hóa
        show_progress_bar=False,
    )
    return vectors.tolist()


def get_collection():
    """Mở hoặc tạo Chroma collection dùng cosine distance."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_documents() -> list[dict]:
    """Đọc mọi .md trong data/standardized/ và trả về list Document."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = unicodedata.normalize(
            "NFC", path.read_text(encoding="utf-8")
        ).strip()
        if not content:
            continue  # bỏ qua file rỗng

        doc_type = "legal" if "legal" in path.parts else "news"
        documents.append(
            {
                "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
                "content": content,
                "metadata": {
                    "source": path.name,
                    "title": path.stem,
                    "doc_type": doc_type,
                    "url": None,  # có thể parse từ header markdown nếu Task 3 đã ghi
                },
            }
        )
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia mỗi Document thành các Chunk có id ổn định và chunk_index."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for document in documents:
        pieces = [p.strip() for p in splitter.split_text(document["content"])]
        # chunk_index liên tục (0..n-1) sau khi bỏ chunk rỗng.
        for index, text in enumerate(p for p in pieces if p):
            chunks.append(
                {
                    "id": f"{document['id']}::chunk-{index}",
                    "content": text,
                    "metadata": {**document["metadata"], "chunk_index": index},
                }
            )
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk (embed theo batch cho nhanh)."""
    if not chunks:
        return chunks
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB (upsert -> chạy lại không tạo trùng)."""
    if not chunks:
        print("No chunks to index.")
        return
    collection = get_collection()

    # Xóa chunk cũ không còn trong lần index này (vd. sau khi đổi cách chunk).
    new_ids = {chunk["id"] for chunk in chunks}
    stale_ids = [i for i in collection.get(include=[])["ids"] if i not in new_ids]
    for start in range(0, len(stale_ids), 500):
        collection.delete(ids=stale_ids[start:start + 500])

    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        # Chroma không nhận giá trị None trong metadata (vd. url); Task 5 sẽ khôi phục.
        metadatas=[
            {k: v for k, v in chunk["metadata"].items() if v is not None}
            for chunk in chunks
        ],
    )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    print(f"Loaded {len(documents)} documents")

    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks")

    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()
