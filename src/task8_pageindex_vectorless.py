"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài:
- Có timeout.
- Có xử lý lỗi.
- Không để pipeline crash.
"""

import json
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()


# =========================================================
# CONFIG
# =========================================================

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")

PAGEINDEX_API_BASE = "https://api.pageindex.ai"

ROOT_DIR = Path(__file__).parent.parent

STANDARDIZED_DIR = ROOT_DIR / "data" / "standardized"

CACHE_DIR = ROOT_DIR / ".pageindex_cache"

CACHE_FILE = CACHE_DIR / "document_ids.json"

UPLOAD_DIR = CACHE_DIR / "uploads"

REQUEST_TIMEOUT = 60


# =========================================================
# CACHE
# =========================================================

def _load_cache() -> dict:
    """Đọc mapping document -> PageIndex doc_id."""

    if not CACHE_FILE.exists():
        return {}

    try:
        return json.loads(
            CACHE_FILE.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict) -> None:
    """Lưu mapping document -> PageIndex doc_id."""

    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    CACHE_FILE.write_text(
        json.dumps(
            cache,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


# =========================================================
# MARKDOWN METADATA
# =========================================================

def _extract_markdown_metadata(path: Path) -> dict:
    """
    Lấy một số metadata từ Markdown đã chuẩn hóa.

    Task 3 news có dạng:

    # Title

    **Source:** URL
    **Crawled:** ...
    """

    text = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    title = path.stem
    url = None

    for line in text.splitlines():

        stripped = line.strip()

        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break

    source_match = re.search(
        r"\*\*Source:\*\*\s*(.+)",
        text,
    )

    if source_match:
        url = source_match.group(1).strip()

    doc_type = (
        "legal"
        if "legal" in path.parts
        else "news"
    )

    return {
        "source": path.name,
        "title": title,
        "doc_type": doc_type,
        "url": url,
    }


# =========================================================
# MARKDOWN -> PDF
# =========================================================

def _find_unicode_font() -> Path:
    """
    Tìm font Unicode để PDF chứa được tiếng Việt.
    """

    candidates = [
        # Windows
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),

        # Linux
        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        ),

        # macOS
        Path("/Library/Fonts/Arial Unicode.ttf"),
    ]

    for path in candidates:
        if path.exists():
            return path

    raise RuntimeError(
        "Không tìm thấy font Unicode để tạo PDF."
    )


def _markdown_to_pdf(
    markdown_path: Path,
    pdf_path: Path,
) -> None:
    """
    Convert Markdown thành PDF tạm để upload PageIndex.
    """

    from fpdf import FPDF

    font_path = _find_unicode_font()

    content = markdown_path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    if not content.strip():
        raise ValueError(
            f"Empty Markdown: {markdown_path}"
        )

    pdf = FPDF()

    pdf.set_auto_page_break(
        auto=True,
        margin=15,
    )

    pdf.add_page()

    pdf.add_font(
        "Unicode",
        fname=str(font_path),
    )

    pdf.set_font(
        "Unicode",
        size=10,
    )

    for line in content.splitlines():

        line = line.replace("\x00", "")

        if not line.strip():
            pdf.ln(3)
            continue

        pdf.multi_cell(
            0,
            6,
            line,
        )

    pdf_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pdf.output(str(pdf_path))


# =========================================================
# UPLOAD DOCUMENTS
# =========================================================

def upload_documents() -> None:
    """
    Upload standardized documents lên PageIndex.

    Cache doc_id để lần chạy sau không upload lại.
    """

    if not PAGEINDEX_API_KEY:
        print(
            "PAGEINDEX_API_KEY chưa có trong .env. "
            "Bỏ qua PageIndex upload."
        )
        return

    if not STANDARDIZED_DIR.exists():
        print(
            f"Standardized directory not found: "
            f"{STANDARDIZED_DIR}"
        )
        return

    cache = _load_cache()

    markdown_files = sorted(
        STANDARDIZED_DIR.rglob("*.md")
    )

    if not markdown_files:
        print("Không có Markdown để upload.")
        return

    for markdown_path in markdown_files:

        relative_path = (
            markdown_path
            .relative_to(STANDARDIZED_DIR)
            .as_posix()
        )

        # ---------------------------------------------
        # Đã upload trước đó -> không upload lại
        # ---------------------------------------------

        if (
            relative_path in cache
            and cache[relative_path].get("doc_id")
        ):
            print(
                f"Cached: {relative_path} "
                f"-> {cache[relative_path]['doc_id']}"
            )
            continue

        metadata = _extract_markdown_metadata(
            markdown_path
        )

        # Prefix legal/news tránh trùng tên
        doc_type = metadata["doc_type"]

        pdf_name = (
            f"{doc_type}__"
            f"{markdown_path.stem}.pdf"
        )

        pdf_path = UPLOAD_DIR / pdf_name

        try:

            # -----------------------------------------
            # Markdown -> PDF
            # -----------------------------------------

            _markdown_to_pdf(
                markdown_path,
                pdf_path,
            )

            print(
                f"Uploading to PageIndex: {pdf_name}"
            )

            # -----------------------------------------
            # Upload PageIndex
            # -----------------------------------------

            with pdf_path.open("rb") as file:

                response = requests.post(
                    f"{PAGEINDEX_API_BASE}/doc/",
                    headers={
                        "api_key": PAGEINDEX_API_KEY,
                    },
                    files={
                        "file": (
                            pdf_name,
                            file,
                            "application/pdf",
                        )
                    },
                    timeout=REQUEST_TIMEOUT,
                )

            response.raise_for_status()

            data = response.json()

            doc_id = data.get("doc_id")

            if not doc_id:
                raise RuntimeError(
                    f"PageIndex không trả doc_id: {data}"
                )

            # -----------------------------------------
            # Cache
            # -----------------------------------------

            cache[relative_path] = {
                "doc_id": doc_id,
                "uploaded_name": pdf_name,
                "source": metadata["source"],
                "title": metadata["title"],
                "doc_type": metadata["doc_type"],
                "url": metadata["url"],
            }

            # Save ngay sau từng upload để nếu crash
            # không mất các doc_id đã upload.
            _save_cache(cache)

            print(
                f"Uploaded: {relative_path} "
                f"-> {doc_id}"
            )

        except Exception as error:

            # External provider không được làm app crash
            print(
                f"PageIndex upload failed "
                f"for {relative_path}: {error}"
            )


# =========================================================
# CITATION PARSER
# =========================================================

def _extract_citations(
    response_data: dict,
    answer: str,
) -> list[dict]:
    """
    Parse citations từ PageIndex response.

    Hỗ trợ cả:
        <doc=file.pdf;page=2;block=...>

    và:
        <cite doc="file.pdf" page="2" block="..."/>
    """

    citations = []

    # -----------------------------------------------------
    # Nếu API trả citations array
    # -----------------------------------------------------

    api_citations = response_data.get(
        "citations",
        [],
    )

    if not api_citations:

        choices = response_data.get(
            "choices",
            [],
        )

        if choices:

            api_citations = (
                choices[0]
                .get("message", {})
                .get("citations", [])
            )

    for citation in api_citations:

        if not isinstance(citation, dict):
            continue

        document = (
            citation.get("doc")
            or citation.get("document")
            or citation.get("file")
            or citation.get("name")
        )

        page = citation.get("page")

        block = (
            citation.get("block")
            or citation.get("block_id")
        )

        if document and page is not None:

            citations.append({
                "doc": str(document),
                "page": int(page),
                "block": block,
            })


    # -----------------------------------------------------
    # Legacy <doc=...>
    # -----------------------------------------------------

    legacy_pattern = re.compile(
        r"<doc=([^;>]+);"
        r"page=(\d+)"
        r"(?:;block=([^>]+))?>"
    )

    for match in legacy_pattern.finditer(answer):

        citations.append({
            "doc": match.group(1),
            "page": int(match.group(2)),
            "block": match.group(3),
        })


    # -----------------------------------------------------
    # Current <cite doc="..." page="..."/>
    # -----------------------------------------------------

    cite_pattern = re.compile(
        r'<cite\s+'
        r'doc="([^"]+)"\s+'
        r'page="(\d+)"'
        r'(?:\s+block="([^"]+)")?'
        r'\s*/?>'
    )

    for match in cite_pattern.finditer(answer):

        citations.append({
            "doc": match.group(1),
            "page": int(match.group(2)),
            "block": match.group(3),
        })


    # -----------------------------------------------------
    # Deduplicate
    # -----------------------------------------------------

    unique = []
    seen = set()

    for citation in citations:

        key = (
            citation["doc"],
            citation["page"],
            citation.get("block"),
        )

        if key not in seen:

            seen.add(key)
            unique.append(citation)

    return unique


# =========================================================
# FETCH EVIDENCE
# =========================================================

def _get_block_text(
    doc_id: str,
    block_id: str,
) -> str:
    """Lấy exact block text nếu citation có block."""

    response = requests.get(
        (
            f"{PAGEINDEX_API_BASE}/doc/"
            f"{doc_id}/block/{block_id}/"
        ),
        headers={
            "api_key": PAGEINDEX_API_KEY,
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    return str(
        data.get("text", "")
    ).strip()


def _get_page_text(
    doc_id: str,
    page_number: int,
) -> str:
    """Lấy Markdown của một page từ PageIndex OCR."""

    response = requests.get(
        f"{PAGEINDEX_API_BASE}/doc/{doc_id}/",
        headers={
            "api_key": PAGEINDEX_API_KEY,
        },
        params={
            "type": "ocr",
            "format": "page",
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    pages = data.get(
        "result",
        [],
    )

    if not isinstance(pages, list):
        return ""

    for page in pages:

        try:
            index = int(
                page.get("page_index", -1)
            )
        except (TypeError, ValueError):
            continue

        if index == page_number:

            return str(
                page.get("markdown", "")
            ).strip()

    return ""


# =========================================================
# SEARCH
# =========================================================

def pageindex_search(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Query PageIndex và trả SearchResult.

    Nếu PageIndex lỗi hoặc chưa cấu hình:
        return []

    Task 9 sẽ tiếp tục dùng hybrid results.
    """

    if not PAGEINDEX_API_KEY:
        return []

    cache = _load_cache()

    # Nếu chưa upload thì thử upload
    if not cache:

        upload_documents()
        cache = _load_cache()

    if not cache:
        return []

    doc_ids = [
        item["doc_id"]
        for item in cache.values()
        if item.get("doc_id")
    ]

    if not doc_ids:
        return []


    try:

        # -------------------------------------------------
        # PageIndex vectorless retrieval/chat
        # -------------------------------------------------

        response = requests.post(
            (
                f"{PAGEINDEX_API_BASE}"
                f"/chat/completions"
            ),
            headers={
                "api_key": PAGEINDEX_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "doc_id": doc_ids,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Find the most relevant evidence "
                            "for the following query. "
                            "Use citations for every piece "
                            "of evidence.\n\n"
                            f"Query: {query}"
                        ),
                    }
                ],
                "stream": False,
                "temperature": 0.0,
                "enable_citations": True,
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        choices = data.get(
            "choices",
            [],
        )

        if not choices:
            return []

        answer = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )

        citations = _extract_citations(
            data,
            answer,
        )

        if not citations:
            return []


        # -------------------------------------------------
        # Lookup cache bằng tên file upload
        # -------------------------------------------------

        by_uploaded_name = {
            item["uploaded_name"]: item
            for item in cache.values()
            if item.get("uploaded_name")
        }

        results = []


        # -------------------------------------------------
        # Citation -> SearchResult
        # -------------------------------------------------

        for rank, citation in enumerate(
            citations,
            1,
        ):

            if len(results) >= top_k:
                break

            doc_name = citation["doc"]

            info = by_uploaded_name.get(
                doc_name
            )

            if not info:
                continue

            doc_id = info["doc_id"]

            block_id = citation.get(
                "block"
            )

            page = citation["page"]

            content = ""

            # Exact block tốt hơn page
            if block_id:

                try:
                    content = _get_block_text(
                        doc_id,
                        block_id,
                    )
                except Exception:
                    content = ""

            # Nếu block không có / lỗi -> lấy cả page
            if not content:

                try:
                    content = _get_page_text(
                        doc_id,
                        page,
                    )
                except Exception:
                    content = ""

            if not content:
                continue

            results.append({
                "id": (
                    f"{doc_id}::"
                    f"page-{page}::"
                    f"{block_id or 'page'}"
                ),

                "content": content,

                # PageIndex không có similarity score
                # nên dùng score giảm theo rank.
                "score": 1.0 / rank,

                "metadata": {
                    "source": info["source"],
                    "title": info["title"],
                    "doc_type": info["doc_type"],
                    "url": info.get("url"),
                    "chunk_index": max(
                        page - 1,
                        0,
                    ),
                },

                "retrieval_method": "pageindex",
            })

        return results


    except Exception as error:

        # Không bao giờ để external provider
        # làm retrieval pipeline crash.
        print(
            f"PageIndex search failed: {error}"
        )

        return []


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    upload_documents()

    results = pageindex_search(
        "Đại học FPT tuyển sinh năm 2026 "
        "bằng những phương thức nào?",
        top_k=3,
    )

    for result in results:

        print(
            result["score"],
            result["metadata"]["title"],
        )

        print(
            result["content"][:300]
        )

        print("-" * 80)