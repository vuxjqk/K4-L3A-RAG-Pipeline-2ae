# Evaluation summary

Started (UTC): 2026-09-20T10:42:46.613490+00:00
Pair generator/judge model: gemini-2.5-flash-lite
Git commit: 3b72d5c42e9e9dd38b52afe1a800c2c5b68cb939
Working-tree fingerprint: c16262abaf1a99fa36e9bf7937e0bbff35959aa10f28560927379f0163f9a002
In-domain cases selected: 15
Complete paired A/B cases: 15

A: dense top-k.
B: dense + BM25 (2*top-k each), RRF k=60, final top-k.
PageIndex disabled in both configs for the A/B comparison.
One Gemini request evaluates BOTH configs for one case to reduce quota usage.
This is LLM-as-judge, NOT Ragas. The same model generates and judges both answers,
which can introduce self-judge/reference leakage bias; this limitation must be reported.

| Metric | A | B | B-A |
|---|---:|---:|---:|
| faithfulness | 0.2667 | 0.8667 | +0.6000 |
| answer_relevancy | 0.0000 | 0.8333 | +0.8333 |
| context_recall | 0.0000 | 0.7667 | +0.7667 |
| context_precision | 0.7333 | 0.8553 | +0.1220 |
| Average | 0.2500 | 0.8305 | +0.5805 |

## Lowest-scoring rows
- Case 6 / A / mean=0.0000: Học phí chuyên ngành tại Hà Nội đã tăng thế nào từ đề án 2022 đến đề án 2024 (học kỳ 1-3)?
  Reason: Context A does not contain any information about tuition fees for specific majors in Hanoi for the 2022 and 2024 schemes, nor does it mention the fee for the first 1-3 semesters.
- Case 12 / A / mean=0.0000: Điểm kết hợp (ĐKH) trong công thức xét tuyển năm 2026 của FPT được tính như thế nào?
  Reason: Context A only contains a link to TikTok and no information about the FPT admission formula.
- Case 14 / A / mean=0.0000: Thí sinh thi tốt nghiệp 2026 đăng ký ngành Luật cần tối thiểu bao nhiêu điểm cho 3 môn thi?
  Reason: Context A does not contain any information about the minimum score required for the Law major for the 2026 graduation exam.

## Rows needing attention
- Case 10 / PAIR: error 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 10, model: gemini-2.5-flash-lite\nPlease retry in 38.12926798s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-flash-lite'}, 'quotaValue': '10'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '38s'}]}}

## Method limitation

Scores are produced by one LLM-as-judge request per case.
The reference answer and expected evidence are visible to the judge.
The same model generates and judges A/B answers, so scores are useful for
a controlled within-run A/B comparison but should not be presented as
independent human judgment or as Ragas metrics.
