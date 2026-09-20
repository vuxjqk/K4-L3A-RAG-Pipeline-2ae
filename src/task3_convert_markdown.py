"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.
"""

import unicodedata
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def normalize_text(text: str) -> str:
    """Chuẩn hóa Unicode về NFC để BM25/embedding khớp với query người dùng."""
    return unicodedata.normalize("NFC", text)


def convert_legal_docs() -> None:
    """Convert PDF/DOCX vào standardized/legal."""

    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"

    output_dir.mkdir(parents=True, exist_ok=True)

    if not legal_dir.exists():
        print(f"Legal directory not found: {legal_dir}")
        return

    converter = MarkItDown()

    for path in legal_dir.iterdir():
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue

        try:
            result = converter.convert(str(path))
            content = normalize_text(result.text_content).strip()

            if not content:
                print(f"Skipped empty legal document: {path.name}")
                continue

            output_path = output_dir / f"{path.stem}.md"

            output_path.write_text(
                content,
                encoding="utf-8"
            )

            print(f"Saved: {output_path}")

        except Exception as error:
            print(f"Failed to convert {path.name}: {error}")

def convert_news_articles() -> None:
    """Convert JSON trong landing/news sang Markdown."""

    import json

    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"

    output_dir.mkdir(parents=True, exist_ok=True)

    if not news_dir.exists():
        print(f"News directory not found: {news_dir}")
        return

    required_fields = {
        "url",
        "title",
        "date_crawled",
        "content_markdown",
    }

    for path in news_dir.glob("*.json"):

        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )

            missing_fields = required_fields - data.keys()

            if missing_fields:
                print(
                    f"Skipped {path.name}: "
                    f"missing {missing_fields}"
                )
                continue

            content = normalize_text(data["content_markdown"]).strip()

            if not content:
                print(f"Skipped empty article: {path.name}")
                continue

            header = (
                f"# {data['title']}\n\n"
                f"**Source:** {data['url']}\n\n"
                f"**Crawled:** {data['date_crawled']}\n\n"
                "---\n\n"
            )

            output_path = output_dir / f"{path.stem}.md"

            output_path.write_text(
                header + content,
                encoding="utf-8"
            )

            print(f"Saved: {output_path}")

        except Exception as error:
            print(f"Failed to convert {path.name}: {error}")


def convert_all() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    convert_legal_docs()
    convert_news_articles()

    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()