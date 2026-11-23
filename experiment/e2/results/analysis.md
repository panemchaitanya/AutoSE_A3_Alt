# E2 mechanical analysis

Derived from `score.json` + `verdict.json` by `experiment/e2/e2_analysis.py`; do not hand-edit the numbers. Cross-checked against `summary.json` (0 inconsistencies).

| Seed | Variant | Verdict | Expected | Verdict correct | Keyword-caught flag | Formal findings | Calls | Tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sp1 | A | request_changes | request_changes | yes | True | 2 | 5 | 26,466 |
| sp1 | B | request_changes | request_changes | yes | True | 1 | 25 | 255,108 |
| sp2 | A | request_changes | request_changes | yes | True | 1 | 4 | 24,721 |
| sp2 | B | approve | request_changes | no | True (disagrees with verdict) | 0 | 15 | 143,574 |
| sp3 | A | approve | request_changes | no | False | 0 | 4 | 17,146 |
| sp3 | B | approve | request_changes | no | False | 0 | 5 | 25,501 |
| sp4 | A | request_changes | request_changes | yes | True | 2 | 6 | 27,432 |
| sp4 | B | approve | request_changes | no | True (disagrees with verdict) | 0 | 5 | 25,887 |
| sp5 | A | request_changes | request_changes | yes | True | 1 | 5 | 25,844 |
| sp5 | B | approve | request_changes | no | True (disagrees with verdict) | 0 | 5 | 25,863 |

- Variant A: verdict-correct 4/5; keyword-caught 4/5; 121,609 tokens across 24 calls.
- Variant B: verdict-correct 1/5; keyword-caught 4/5; 475,933 tokens across 55 calls.
- Token ratio B/A: 3.91x.
- Verdict flips from correct-under-A to wrong-under-B: 3 of 5.

Catch rates quoted in the report are verdict-correct rates. The keyword-caught flag is retained above because it can disagree with the verdict (flag true, verdict approve, zero formal findings): those rows are where the reviewer wrote the defect into its own output and approved anyway. That disagreement is evidence for the influence claim and is listed as a metric limitation in report section 6.
