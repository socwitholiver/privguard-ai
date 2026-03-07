# Fairness, Safety, and Limits (Round 1)

This document states current safeguards and known limits in the MVP.

## 1) Fairness posture (current)

- The MVP relies primarily on pattern/rule detection and OCR, not a black-box classifier for eligibility or ranking decisions.
- This reduces some model-opinion bias risk, but does **not** remove all fairness risk.

## 2) Potential bias or failure points

- OCR quality can vary by scan quality, lighting, and document language/layout.
- Pattern detection may miss uncommon formats or over-flag unusual text.
- Documents with non-standard formatting may have lower extraction quality.

## 3) Current safeguards

- Human-readable findings are shown before action.
- Risk output is transparent (score + level + insights).
- Redaction quality verification checks for leaks after protection.
- Audit logs preserve traceability for operational review.

## 4) Responsible-use guidance

- Do not use MVP output as the sole source of truth for punitive decisions.
- Keep a human-in-the-loop for high-risk or ambiguous documents.
- Use verification output (PASS/FAIL, coverage, leaks) before sharing redacted files.

## 5) Near-term fairness improvements (post Round 1)

- Add format-variance test cases for Kenyan contact/ID representations.
- Add OCR confidence thresholds and warnings for low-confidence extractions.
- Add language/format regression tests to reduce inconsistent outcomes.
- Track false positives/false negatives during pilot and tune detection rules.

## 6) Submission note for judges

In Round 1, clearly acknowledge:

- what the MVP does reliably now,
- where fairness/accuracy can fail,
- what controls are already in place,
- and your concrete mitigation roadmap.
