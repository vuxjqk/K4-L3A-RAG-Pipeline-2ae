"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()


TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "")

SAFE_REFUSAL = (
    "Tôi không thể xác minh thông tin này từ nguồn hiện có."
)

SYSTEM_PROMPT = """
Bạn là chatbot RAG.

Chỉ được trả lời dựa trên context được cung cấp.

Mỗi thông tin quan trọng trong câu trả lời phải có citation
theo đúng dạng [Document N].

Không được tự tạo nguồn hoặc sử dụng kiến thức bên ngoài context.

Nếu context không đủ để trả lời, hãy nói:
"Tôi không thể xác minh thông tin này từ nguồn hiện có."
""".strip()


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """
    Đưa các chunks quan trọng về đầu và cuối context.

    Không thay đổi list chunks ban đầu.
    """

    if len(chunks) <= 2:
        return list(chunks)

    front = chunks[::2]
    back = chunks[1::2]

    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """
    Chuyển danh sách chunks thành context cho LLM.

    Mỗi chunk có:
    - Document number
    - Title
    - Source
    - Content
    """

    parts = []

    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]

        title = metadata.get("title", "Unknown")
        source = metadata.get("source", "Unknown")

        parts.append(
            f"[Document {index} | "
            f"Title: {title} | "
            f"Source: {source}]\n"
            f"{chunk['content']}"
        )

    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """
    Gọi LLM provider được cấu hình trong .env.

    Hỗ trợ:
    - OpenAI
    - Gemini
    - Anthropic
    """

    if not LLM_MODEL:
        raise ValueError("LLM_MODEL chưa được cấu hình trong .env")

    # -----------------------
    # OpenAI
    # -----------------------

    if LLM_PROVIDER == "openai":

        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY chưa được cấu hình trong .env"
            )

        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )

        return response.choices[0].message.content or ""


    # -----------------------
    # Gemini
    # -----------------------

    elif LLM_PROVIDER == "gemini":

        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY chưa được cấu hình trong .env"
            )

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            ),
        )

        return response.text or ""


    # -----------------------
    # Anthropic Claude
    # -----------------------

    elif LLM_PROVIDER == "anthropic":

        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY chưa được cấu hình trong .env"
            )

        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=1024,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
        )

        texts = []

        for block in response.content:
            if getattr(block, "type", None) == "text":
                texts.append(block.text)

        return "\n".join(texts)


    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}"
        )


def generate_with_citation(
    query: str,
    top_k: int = TOP_K
) -> dict:
    """
    Chạy toàn bộ Generation stage của RAG.

    Query
        ↓
    Retrieval
        ↓
    Top-k chunks
        ↓
    Context
        ↓
    LLM
        ↓
    Answer + sources
    """

    # -----------------------
    # 1. Retrieval
    # -----------------------

    chunks = retrieve(
        query,
        top_k=top_k,
    )

    # Không có evidence
    if not chunks:
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
        }


    # -----------------------
    # 2. Reorder chunks
    # -----------------------

    reordered = reorder_for_llm(chunks)


    # -----------------------
    # 3. Format context
    # -----------------------

    context = format_context(reordered)


    # -----------------------
    # 4. Tạo message cho LLM
    # -----------------------

    user_message = (
        f"Context:\n"
        f"{context}\n\n"
        f"Question:\n"
        f"{query}"
    )


    # -----------------------
    # 5. Generation
    # -----------------------

    try:

        answer = call_llm(
            SYSTEM_PROMPT,
            user_message,
        )

        if not answer.strip():
            return {
                "answer": SAFE_REFUSAL,
                "sources": [],
                "retrieval_source": "none",
            }

    except Exception as error:

        print(f"LLM provider error: {error}")

        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
        }


    # -----------------------
    # 6. Retrieval source
    # -----------------------

    method = chunks[0]["retrieval_method"]

    if method == "pageindex":
        retrieval_source = "pageindex"
    else:
        retrieval_source = "hybrid"


    # -----------------------
    # 7. GenerationResult
    # -----------------------

    return {
        "answer": answer,
        "sources": reordered,
        "retrieval_source": retrieval_source,
    }


if __name__ == "__main__":

    result = generate_with_citation(
        "Đại học FPT tuyển sinh năm 2026 bằng những phương thức nào?"
    )

    print(result)