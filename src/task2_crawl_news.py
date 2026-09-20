"""
Task 2 — Crawl bài viết/thông báo.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cài browser trước khi chạy:
    python -m playwright install chromium
    
-> Dùng Firecrawl or bất cứ công cụ nào bạn quen    
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from crawl4ai import AsyncWebCrawler


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://daihoc.fpt.edu.vn/quy-che-tuyen-sinh-2026/",
    "https://daihoc.fpt.edu.vn/phuong-thuc-tuyen-sinh/",
    "https://daihoc.fpt.edu.vn/thong-bao-tuyen-sinh/thong-bao-tuyen-sinh-truong-dai-hoc-fpt-he-dai-hoc-chinh-quy-nam-2026/",
    "https://daihoc.fpt.edu.vn/hoc-phi-tai-campus-ha-noi/",
    "https://daihoc.fpt.edu.vn/thong-bao-tuyen-sinh/huong-dan-nop-ho-so-dang-ky-chuong-trinh-tim-kiem-nhan-tai-ky-nguyen-so-viet-nam-2026/",
]


async def crawl_article(url: str) -> dict:
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)

        return {
            "url": url,
            "title": result.metadata.get("title", "Unknown"),
            "date_crawled": datetime.now().isoformat(),
            "content_markdown": str(result.markdown),
        }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(ARTICLE_URLS, 1):
        try:
            article = await crawl_article(url)
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output}")
        except Exception as error:
            print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
