# Fairness, Safety, and Limits

This document is the governance note for the current MVP.

## What the MVP Does Today

PrivGuard is not a predictive policing, eligibility, ranking, or targeting system. It is a records-protection workflow that detects sensitive entities, applies a local protection policy, and preserves audit traces.

That design choice reduces some fairness risk because the system is not deciding who should be punished, prioritized, or excluded. It is deciding how a document should be protected.

## Main Failure Modes

Current risks remain real:

- OCR quality can degrade on low-quality scans, photos, handwritten marks, or unusual layouts.
- Regex and rule-based detection can miss uncommon formats.
- Non-standard document language or formatting can cause both over-flagging and under-detection.
- Operators may over-trust a clean result even when extraction quality is weak.

## Current Safeguards

The MVP already includes the following controls:

- transparent findings and risk summaries rather than opaque decisions,
- explicit redaction-quality verification,
- audit logs for operational review,
- local storage and encryption for sensitive artifacts,
- human-readable lifecycle status and vault actions,
- a workflow that supports human review for high-risk or expired records.

## Responsible-Use Guidance

Use these statements in the pitch and documentation:

- `PrivGuard is a decision-support and privacy-protection tool, not a final adjudicator.`
- `High-risk or ambiguous cases should remain subject to human review.`
- `A protected output should not be shared unless verification status is acceptable.`
- `Poor OCR conditions should trigger operator caution and, where necessary, re-scanning.`

## Misuse Considerations

Judges will expect evidence that misuse has been considered.

Current concerns:

- an operator may rely on a low-quality extraction,
- a malicious user may attempt to bypass the watch-folder workflow,
- demo credentials or demo secrets could be mistaken for production practice,
- a document may be wrongly considered safe due to a missed pattern.

Current mitigations:

- local-only operation limits unnecessary external data exposure,
- vault actions are gated by authentication and vault state,
- the repo now separates tracked config from local secret overrides,
- audit logs preserve a reconstruction trail for supervisors and reviewers.

## Fairness Position

Because the MVP is rule- and policy-driven, the main fairness challenge is coverage consistency rather than model bias in social ranking decisions.

The immediate fairness work should focus on:

- wider format coverage for Kenyan IDs, phones, and document layouts,
- multilingual and layout-variant regression tests,
- OCR confidence warnings,
- documented operator guidance for low-confidence results.

## What We Will Add Next

To improve Stage 2 readiness:

- label a representative evaluation set and track false positives and false negatives,
- add OCR confidence thresholds and warning banners,
- record extraction-confidence metadata in audit trails,
- expand tests for edge cases across document types and Kenyan formatting variants.

## Judge Summary

A fair description of the current state is:

`PrivGuard already implements privacy, auditability, and human-review safeguards appropriate for an MVP, but it should still be presented as an operator-assist records-protection tool rather than an autonomous authority.`
