# RAG evaluation results

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | 2026-09-20 |
| Framework and version | Custom LLM-as-judge A/B evaluation |
| Evaluator model | Gemini 2.5 Flash Lite |
| Generator model | Gemini 2.5 Flash Lite |
| Embedding model | BAAI/bge-m3 |
| Corpus version/commit | 3b72d5c |
| Golden dataset size | 23 total cases; 15 in-domain cases evaluated |
| `top_k` | 5 |
| Fallback threshold and calibration | 0.3; PageIndex fallback excluded from the controlled A/B comparison |

## Configurations

- **Config A — dense-only:** Dense semantic retrieval sử dụng BAAI/bge-m3 + ChromaDB, lấy trực tiếp top-5 chunks.
- **Config B — hybrid + RRF:** Dense top-10 + BM25 top-10, sau đó fuse một lần bằng Reciprocal Rank Fusion (RRF, k=60) và lấy final top-5 chunks.

Both configurations use the same dataset, generation/evaluation model, prompt, context reordering strategy, and `top_k`.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      | 0.2667 | 0.8667 | +0.6000 |
| Answer relevance  | 0.0000 | 0.8333 | +0.8333 |
| Context recall    | 0.0000 | 0.7667 | +0.7667 |
| Context precision | 0.7333 | 0.8553 | +0.1220 |
| **Average**       | 0.2500 | 0.8305 | +0.5805 |

## A/B comparison

- Cấu hình tốt hơn trong evaluation run này: **Config B — hybrid + RRF**.
- Evidence: average score tăng từ 0.2500 lên 0.8305 (+0.5805). Config B cũng có answer relevance 0.8333, context recall 0.7667 và context precision 0.8553, đều cao hơn Config A trong run này.
- Trade-off về latency/cost: Config B thực hiện thêm BM25 retrieval và RRF fusion nên có thêm local retrieval computation. Cả hai cấu hình được đánh giá bằng cùng model và cùng số lượng paired cases. Evaluation sử dụng Gemini LLM-as-judge nên kết quả có thể chịu self-judge/reference leakage bias.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ----------------- | ---------- |
| 1 | Học phí chuyên ngành tại Hà Nội đã tăng thế nào từ đề án 2022 đến đề án 2024 (học kỳ 1-3)? | A — dense-only | 0.0000 | 0.0000 | 0.0000 | 0.0000 | retrieval | Dense retrieval không lấy được các chunk chứa thông tin học phí chuyên ngành tại Hà Nội của cả đề án 2022 và 2024, nên model không có bằng chứng để trả lời câu hỏi so sánh. |
| 2 | Điểm kết hợp (ĐKH) trong công thức xét tuyển năm 2026 của FPT được tính như thế nào? | A — dense-only | 0.0000 | 0.0000 | 0.0000 | 0.0000 | retrieval / data quality | Context được retrieve chỉ chứa liên kết TikTok và không chứa công thức xét tuyển hoặc định nghĩa ĐKH, cho thấy retrieval đã chọn chunk có hàm lượng thông tin thấp. |
| 3 | Thí sinh thi tốt nghiệp 2026 đăng ký ngành Luật cần tối thiểu bao nhiêu điểm cho 3 môn thi? | A — dense-only | 0.0000 | 0.0000 | 0.0000 | 0.0000 | retrieval | Dense retrieval không lấy được chunk chứa ngưỡng điểm tối thiểu cho ngành Luật năm 2026, vì vậy generation không có đủ evidence để trả lời. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
| 1 | Sử dụng hybrid retrieval (dense + BM25 + RRF) làm retrieval strategy chính thay cho dense-only | Cả 3 worst-performing rows đều thuộc Config A, trong khi Config B đạt average 0.8305 so với 0.2500 của Config A | Tăng khả năng tìm đúng các chunk có keyword quan trọng như năm tuyển sinh, ngành học, học phí và công thức xét tuyển | Chạy lại Cases 6, 12 và 14 với Config B và kiểm tra context recall, precision và answer relevance |
| 2 | Lọc hoặc giảm trọng số các chunk có hàm lượng thông tin thấp như link-only / metadata-only | Case 12 retrieve một context chỉ chứa liên kết TikTok và không chứa nội dung về công thức ĐKH | Giảm retrieval noise và tăng context precision | Kiểm tra top-k retrieved chunks sau khi lọc và xác nhận các chunk link-only không còn xuất hiện ở vị trí cao |
| 3 | Cải thiện retrieval cho câu hỏi có nhiều ràng buộc như năm, ngành, địa điểm và so sánh nhiều tài liệu | Case 6 cần thông tin từ cả đề án 2022 và 2024; Case 14 cần đúng năm 2026 và đúng ngành Luật | Tăng context recall cho các câu multi-hop hoặc có nhiều điều kiện cụ thể | Re-run các câu hỏi multi-hop/year-specific và so sánh context recall trước và sau thay đổi |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Not performed | N/A | N/A | N/A | No bonus experiment was performed. |