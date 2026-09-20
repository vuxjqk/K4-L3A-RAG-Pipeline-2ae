# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Bá Chinh
- Mã học viên: 2A202602654
- Nhóm: K4-L3A-RAG-Pipeline-2ae
- Repository/branch: https://github.com/vuxjqk/K4-L3A-RAG-Pipeline-2ae — `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 2 — Data ingestion | Tham gia xử lý dữ liệu đầu vào và chuẩn bị dữ liệu cho pipeline | `src/task2_*.py` | Done |
| Task 3 — Standardization | Chuẩn hóa tài liệu legal/news sang Markdown, giữ metadata và cấu trúc thư mục | `src/task3_*.py`, `data/standardized/` | Done |
| Task 6 — Lexical retrieval | Triển khai BM25 lexical search và chuẩn bị corpus cho hybrid retrieval | `src/task6_lexical_search.py` | Done |
| Task 8 — Retrieval pipeline | Tham gia tích hợp luồng retrieval giữa các module và kiểm tra đầu ra retrieval | `src/task8_*.py` | Done |
| Task 10 — Generation | Kiểm tra generation/citation và sửa mapping giữa thứ tự context đưa vào LLM với danh sách sources trả về | `src/task10_generation.py` | Done |
| Streamlit application | Tích hợp pipeline vào giao diện chatbot, hiển thị câu trả lời, retrieval source và sources | `app.py` | Done |
| Evaluation | Thực hiện A/B evaluation giữa dense-only và hybrid + RRF; phân tích lỗi retrieval và hoàn thiện báo cáo | `run_evaluation_low_quota.py`, `group_project/evaluation/full_low/`, `group_project/evaluation/RESULT.md` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** So sánh dense-only với hybrid retrieval gồm dense + BM25 + Reciprocal Rank Fusion trong cùng điều kiện `top_k=5`.

   **Lý do/evidence:** Kết quả evaluation trên 15 paired in-domain cases cho thấy Config A có average score 0.2500, trong khi Config B đạt 0.8305. Các worst-performing cases của Config A đều thất bại do không retrieve được evidence cần thiết.

   **Trade-off:** Hybrid retrieval cần thêm BM25 và bước RRF nên có thêm chi phí xử lý local, nhưng đổi lại retrieval recall và chất lượng context tốt hơn trong evaluation hiện tại.

2. **Quyết định:** Chuyển evaluation cuối sang custom LLM-as-judge dùng Gemini 2.5 Flash Lite thay vì tiếp tục full Ragas evaluation.

   **Lý do/evidence:** Ragas evaluation ban đầu gặp Gemini API quota `429 RESOURCE_EXHAUSTED`. Phiên bản low-quota chỉ sử dụng một Gemini request cho mỗi case để đánh giá cả Config A và B, nhờ đó hoàn thành được 15 paired cases trong giới hạn quota.

   **Trade-off:** Cùng một model được sử dụng để generate và judge nên có nguy cơ self-judge/reference leakage bias. Vì vậy kết quả được sử dụng cho so sánh A/B trong cùng run, không được coi là đánh giá độc lập của con người.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - `pytest -q`
  - A/B evaluation trên 15 in-domain cases từ golden dataset gồm 23 cases.
  - So sánh Config A: dense-only top-5 với Config B: dense top-10 + BM25 top-10 + RRF, final top-5.

- Kết quả trước/sau nếu có:
  - Config A average: `0.2500`
  - Config B average: `0.8305`
  - Delta B−A: `+0.5805`
  - Answer relevance: `0.0000 → 0.8333`
  - Context recall: `0.0000 → 0.7667`
  - Context precision: `0.7333 → 0.8553`

- Lỗi đã phát hiện và cách xử lý:
  - Phát hiện Gemini API bị giới hạn quota khi chạy Ragas evaluation.
  - Chuyển sang low-quota evaluation và hỗ trợ `--resume` để không mất các case đã chấm.
  - Phát hiện dense-only retrieval thất bại ở một số câu hỏi về học phí, công thức xét tuyển và điều kiện theo năm/ngành.
  - Kiểm tra và sửa mapping giữa reordered context và sources trong Task 10 để citation/source nhất quán hơn.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm:
  - Evaluation cuối chỉ chạy trên 15 in-domain cases và sử dụng cùng Gemini 2.5 Flash Lite cho cả generation và judging, nên vẫn tồn tại self-judge bias. Ngoài ra các out-of-domain cases chưa được đưa vào cùng bộ 4 metric.

- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện:
  - Tách evaluator khỏi generator, chạy lại toàn bộ 23 golden cases bằng một evaluator độc lập và bổ sung riêng metric cho safe refusal/out-of-domain queries.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Nguyễn Bá Chinh
