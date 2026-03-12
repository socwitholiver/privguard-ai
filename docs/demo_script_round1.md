# Judge-Facing Demo Script

## 2-Minute Version

1. `Open with national relevance`
   - "PrivGuard AI is an offline-first records-protection system for Kenyan public-sector and critical-service document workflows."
   - "It is designed for agencies that cannot send sensitive citizen or payroll records to foreign cloud services."

2. `Show live intake`
   - Open the dashboard and use `WATCH FOLDER`.
   - Explain that the watched folder is the operational inbox for inbound records.

3. `Show automated protection`
   - Point to a newly processed file.
   - Show detected entities, risk level, and the final action: allow, redact, or redact plus encrypt.

4. `Show trust controls`
   - Open the vault view.
   - Point to local storage, lifecycle status, and audit activity.

5. `Close with value`
   - "The MVP reduces manual handling risk by turning privacy controls into an auditable local workflow."

## 6-8 Minute Version

### Part A: Problem and sector fit

Use this framing:

- public-sector HR and payroll offices handle documents with IDs, salaries, contacts, and passwords,
- citizen-service and admissions offices handle records with names, IDs, and contact data,
- these workflows often need on-prem or low-connectivity operation.

### Part B: Live workflow

Show:

- watch-folder intake,
- live scan progression,
- recent activity table,
- protected-output generation,
- vault storage.

### Part C: Security and governance

Say explicitly:

- data stays local,
- high-risk originals are encrypted,
- audit logs preserve what happened and why,
- lifecycle controls govern archive and deletion actions,
- the system supports human review rather than replacing accountable oversight.

### Part D: Technical evidence

Reference:

- benchmark results from [performance_benchmarks.md](/C:/Users/HP/Desktop/privguard-ai/docs/performance_benchmarks.md),
- safety notes from [fairness_and_limits.md](/C:/Users/HP/Desktop/privguard-ai/docs/fairness_and_limits.md),
- test-backed workflow coverage in the repo.

### Part E: Deployment story

Use this line:

- "An agency can deploy this as a local workstation or on-prem records-protection layer in front of existing filing, HR, admissions, or records-management systems."

## Questions Judges May Ask

### Why is this nationally relevant?

Because it protects sensitive public and operational records locally, reducing exposure risk and dependency on external cloud processing.

### What makes this AI and not just a file tool?

The system combines extraction, sensitive-entity detection, risk scoring, and policy-driven protection actions into one automated workflow.

### Is it production-ready?

No. It is an MVP with real workflow value, but it still needs stronger benchmark evidence, integration packaging, and broader evaluation coverage.

### How do you handle trust and misuse?

By keeping data local, encrypting high-risk originals, logging actions, showing explainable findings, and positioning the system as operator-assist rather than autonomous authority.

## Demo Safety Notes

- Use synthetic or consented files only.
- Avoid showing live secrets or local demo PINs.
- Keep one fallback text file and one fallback image or PDF ready.
- If OCR is slow, narrate why extraction-heavy formats take longer than text-native files.
