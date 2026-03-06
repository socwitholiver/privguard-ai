# Demo documents

Synthetic documents for testing PRIVGUARD AI (scan, protect, verify). **No real personal data.**

## Contents

| File | Description |
|------|-------------|
| **sensitive_demo.pdf** | PDF with synthetic sensitive content: Kenyan national IDs, KRA PINs, phone numbers (+254…), emails. Use for scan/protect demos. |
| **kenyan_id_sample.jpg** | Mock Kenyan national identity card (sample only). Shows placeholder fields: name, ID number, DOB, gender, phone. Clearly labelled "SAMPLE – NOT OFFICIAL". |
| **kenyan_driving_license_sample.jpg** | Mock Kenyan driving licence (sample only). Placeholder fields: holder, licence number, ID number, class, validity, mobile. Labelled "SAMPLE – NOT OFFICIAL". |
| **school_admission_sample.txt** | Text sample: student/parent details (synthetic). |
| **sme_payroll_sample.txt** | Text sample: payroll-style employee data (synthetic). |

## Regenerating PDF and JPGs

To recreate `sensitive_demo.pdf`, `kenyan_id_sample.jpg`, and `kenyan_driving_license_sample.jpg`:

```bash
python demo_docs/generate_demo_assets.py
```

Requires: Pillow (for JPGs). PyMuPDF (fitz) is optional; if missing, the script writes a minimal PDF with the same text.

## Demo safety

- Use **synthetic or consented data only** in demos.
- Do not expose real personal identifiers in public demos.
- The ID and licence images are **mock-ups** for testing OCR and detection only.
