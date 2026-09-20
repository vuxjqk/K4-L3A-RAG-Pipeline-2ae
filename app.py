import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="FPT Admission RAG Chatbot",
    page_icon="🎓",
    layout="wide",
)


# =========================================================
# SESSION STATE
# =========================================================

if "messages" not in st.session_state:
    st.session_state.messages = []


# =========================================================
# HELPER: HIỂN THỊ SOURCES
# =========================================================

def display_sources(sources: list[dict]) -> None:
    """Hiển thị nguồn retrieval bên dưới câu trả lời."""

    if not sources:
        return

    with st.expander("Nguồn tham khảo"):
        for index, source in enumerate(sources, 1):

            metadata = source.get("metadata", {})

            title = metadata.get(
                "title",
                "Unknown"
            )

            source_name = metadata.get(
                "source",
                "Unknown"
            )

            url = metadata.get("url")

            score = source.get(
                "score",
                0.0
            )

            method = source.get(
                "retrieval_method",
                "unknown"
            )

            st.markdown(
                f"### Document {index}: {title}"
            )

            st.write(
                f"**Source:** {source_name}"
            )

            st.write(
                f"**Retrieval method:** {method}"
            )

            st.write(
                f"**Score:** {score:.4f}"
            )

            if url:
                st.markdown(
                    f"**URL:** {url}"
                )

            # Hiển thị một phần nội dung chunk
            content = source.get("content", "")

            if content:
                st.caption(
                    content[:500]
                    + ("..." if len(content) > 500 else "")
                )

            st.divider()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title("FPT Admission RAG")

    st.caption(
        "Chatbot hỗ trợ tra cứu thông tin "
        "tuyển sinh Đại học FPT năm 2026."
    )

    top_k = st.slider(
        "Số chunks sử dụng",
        min_value=3,
        max_value=10,
        value=5,
    )

    if st.button("Xóa lịch sử chat"):
        st.session_state.messages = []
        st.rerun()


# =========================================================
# MAIN PAGE
# =========================================================

st.title("🎓 FPT University Admission Chatbot")

st.caption(
    "Hỏi về phương thức tuyển sinh, học phí, "
    "quy chế và các thông tin tuyển sinh Đại học FPT năm 2026."
)


# =========================================================
# HIỂN THỊ LỊCH SỬ CHAT
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(
            message["content"]
        )

        # Chỉ assistant mới có source
        if message["role"] == "assistant":

            retrieval_source = message.get(
                "retrieval_source"
            )

            if retrieval_source:
                st.caption(
                    f"Retrieval: {retrieval_source}"
                )

            display_sources(
                message.get(
                    "sources",
                    []
                )
            )


# =========================================================
# USER INPUT
# =========================================================

query = st.chat_input(
    "Ví dụ: Đại học FPT tuyển sinh năm 2026 bằng những phương thức nào?"
)


# =========================================================
# GENERATION
# =========================================================

if query:

    # -----------------------------------------------------
    # 1. Lưu câu hỏi user
    # -----------------------------------------------------

    st.session_state.messages.append({
        "role": "user",
        "content": query,
    })


    # -----------------------------------------------------
    # 2. Hiển thị câu hỏi
    # -----------------------------------------------------

    with st.chat_message("user"):

        st.markdown(query)


    # -----------------------------------------------------
    # 3. Gọi RAG pipeline
    # -----------------------------------------------------

    with st.chat_message("assistant"):

        with st.spinner(
            "Đang tìm kiếm tài liệu..."
        ):

            try:

                result = generate_with_citation(
                    query,
                    top_k=top_k,
                )

                answer = result.get(
                    "answer",
                    "Không có câu trả lời."
                )

                sources = result.get(
                    "sources",
                    []
                )

                retrieval_source = result.get(
                    "retrieval_source",
                    "none"
                )


            except Exception as error:

                answer = (
                    "Hệ thống hiện không thể xử lý "
                    "câu hỏi này."
                )

                sources = []

                retrieval_source = "none"

                st.error(
                    f"Pipeline error: {error}"
                )


        # -------------------------------------------------
        # 4. Hiển thị answer
        # -------------------------------------------------

        st.markdown(answer)


        # -------------------------------------------------
        # 5. Hiển thị retrieval method
        # -------------------------------------------------

        st.caption(
            f"Retrieval: {retrieval_source}"
        )


        # -------------------------------------------------
        # 6. Hiển thị sources
        # -------------------------------------------------

        display_sources(sources)


    # -----------------------------------------------------
    # 7. Lưu assistant response vào session
    # -----------------------------------------------------

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "retrieval_source": retrieval_source,
    })