# Evaluation summary

Started (UTC): 2026-09-20T10:42:12.530539+00:00
Pair generator/judge model: gemini-2.5-flash-lite
Git commit: 3b72d5c42e9e9dd38b52afe1a800c2c5b68cb939
Working-tree fingerprint: c16262abaf1a99fa36e9bf7937e0bbff35959aa10f28560927379f0163f9a002
In-domain cases selected: 2
Complete paired A/B cases: 2

A: dense top-k.
B: dense + BM25 (2*top-k each), RRF k=60, final top-k.
PageIndex disabled in both configs for the A/B comparison.
One Gemini request evaluates BOTH configs for one case to reduce quota usage.
This is LLM-as-judge, NOT Ragas. The same model generates and judges both answers,
which can introduce self-judge/reference leakage bias; this limitation must be reported.

| Metric | A | B | B-A |
|---|---:|---:|---:|
| faithfulness | 0.0000 | 1.0000 | +1.0000 |
| answer_relevancy | 0.0000 | 1.0000 | +1.0000 |
| context_recall | 0.0000 | 1.0000 | +1.0000 |
| context_precision | 1.0000 | 1.0000 | +0.0000 |
| Average | 0.2500 | 1.0000 | +0.7500 |

## Lowest-scoring rows
- Case 1 / A / mean=0.2500: Theo đề án tuyển sinh 2024, học phí kỳ định hướng tại cơ sở Hà Nội và phân hiệu TP.HCM là bao nhiêu?
  Reason: Context A only contains a link to TikTok and no information about tuition fees.
- Case 2 / A / mean=0.2500: Năm 2024, học phí chuyên ngành từ học kỳ 1 đến học kỳ 3 tại Hà Nội và TP.HCM là bao nhiêu mỗi kỳ?
  Reason: Context A only contains a TikTok link and no information about tuition fees.
- Case 1 / B / mean=1.0000: Theo đề án tuyển sinh 2024, học phí kỳ định hướng tại cơ sở Hà Nội và phân hiệu TP.HCM là bao nhiêu?
  Reason: Context B (Chunks 4 and 5) directly states the tuition fee for the orientation period at the Hanoi campus and Ho Chi Minh City branch is 11,900,000 VNĐ, applicable to new students and consisting of one orientation period.

## Method limitation

Scores are produced by one LLM-as-judge request per case.
The reference answer and expected evidence are visible to the judge.
The same model generates and judges A/B answers, so scores are useful for
a controlled within-run A/B comparison but should not be presented as
independent human judgment or as Ragas metrics.
