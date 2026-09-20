# Evaluation summary

Started (UTC): 2026-09-20T10:30:44.663464+00:00
Generator: gemini-2.5-flash; evaluator: gemini-2.5-flash
Git commit: 3b72d5c42e9e9dd38b52afe1a800c2c5b68cb939; working-tree fingerprint: 6bc0ad1ce00bd078db325bae0818486275647c517aeac31002218c4fbfae610c
In-domain cases selected: 2
Complete paired A/B cases: 0

A: dense top-k. B: dense + BM25 (2*top-k each), RRF k=60, final top-k.
PageIndex disabled in both; fallback calibration is a separate experiment.
Both configs use the same generation prompt and context reorder.
Timing includes retrieval + generation; not evaluator calls. Warm-up runs before timing.
Same generator/evaluator model can introduce judge bias. No monetary cost measured.

| Metric | A | B | B-A |
|---|---:|---:|---:|
| faithfulness | N/A | N/A | N/A |
| answer_relevancy | N/A | N/A | N/A |
| context_recall | N/A | N/A | N/A |
| context_precision | N/A | N/A | N/A |

## Rows needing attention
- 1 / B: error 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash\nPlease retry in 27.143718813s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-flash'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '27s'}]}}

## Lowest-scoring rows (inspect raw.json before assigning root cause)
- 1 / A: Theo đề án tuyển sinh 2024, học phí kỳ định hướng tại cơ sở Hà Nội và phân hiệu TP.HCM là bao nhiêu?

Out-of-domain rows in raw.json require manual refusal review.
This summary does not replace RESULT.md or claim the project is complete.
