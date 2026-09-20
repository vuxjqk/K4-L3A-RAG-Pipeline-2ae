"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


# Chủ đề: Đề án tuyển sinh Đại học FPT (học phí, học bổng, phương thức xét tuyển...).
# Tên file khớp với các file đã tải thủ công vào data/landing/legal/.
SOURCES = {
    "DE-AN-TUYEN-SINH-2024.pdf": "https://daihoc.fpt.edu.vn/wp-content/uploads/2024/06/DE-AN-TUYEN-SINH-2024.pdf",
    "DE-AN-TUYEN-SINH-2023-upweb.pdf": "https://daihoc.fpt.edu.vn/wp-content/uploads/2023/11/DE-AN-TUYEN-SINH-2023-upweb.pdf",
    "de-an-tuyen-sinh-2022-upweb.pdf": "https://daihoc.fpt.edu.vn/wp-content/uploads/2022/06/de-an-tuyen-sinh-2022-upweb.pdf",
}


def _is_valid_pdf(path: Path) -> bool:
    """File tồn tại, không rỗng và có chữ ký PDF."""
    if not path.is_file() or path.stat().st_size == 0:
        return False
    with path.open("rb") as file:
        return file.read(5) == b"%PDF-"


def download_documents() -> None:
    """Đảm bảo có đủ PDF trong data/landing/legal/.

    File đã có (tải thủ công hoặc từ lần chạy trước) được giữ nguyên;
    chỉ tải những file còn thiếu hoặc hỏng.
    """
    import requests

    for filename, url in SOURCES.items():
        path = DATA_DIR / filename
        if _is_valid_pdf(path):
            print(f"Exists: {path.name} ({path.stat().st_size / 1024:.0f} KB)")
            continue

        print(f"Downloading: {url}")
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
        except requests.RequestException as error:
            print(f"Failed: {filename} ({error}). Hãy tải thủ công vào {DATA_DIR}")
            continue
        if not response.content.startswith(b"%PDF-"):
            print(f"Failed: {filename} không phải PDF hợp lệ")
            continue
        path.write_bytes(response.content)
        print(f"Saved: {path.name}")

    missing = [name for name in SOURCES if not _is_valid_pdf(DATA_DIR / name)]
    if missing:
        print(f"Missing {len(missing)} file(s): {', '.join(missing)}")
    else:
        print(f"OK: {len(SOURCES)} legal documents in {DATA_DIR}")


if __name__ == "__main__":
    setup_directory()
    download_documents()
