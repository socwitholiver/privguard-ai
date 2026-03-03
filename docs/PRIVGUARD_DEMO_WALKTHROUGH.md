# PrivGuard AI — Feature Walkthrough & Demo Guide

This guide walks through **every feature** of PrivGuard AI and **how to demonstrate** each one using the synthetic data in `demo_docs/`.

---

## Before you start

### 1. Run PrivGuard

From the project root:

```powershell
cd C:\Users\HP\Desktop\privguard-ai
python app.py
```

Open in the browser: **http://127.0.0.1:5000**

### 2. Synthetic demo data (no real PII)

| File | Use for |
|------|--------|
| `demo_docs/school_admission_sample.txt` | Quick scan/protect: student name, National ID, parent phone, email, KRA PIN. |
| `demo_docs/sme_payroll_sample.txt` | Scan/protect: two employees with IDs, phones, emails, KRA PINs. |
| `demo_docs/sensitive_demo.pdf` | PDF scan/protect: multiple IDs, KRA PINs, phones, emails. |
| `demo_docs/kenyan_id_sample.jpg` | Image/OCR: mock Kenyan ID (name, ID no, DOB, phone). |
| `demo_docs/kenyan_driving_license_sample.jpg` | Image/OCR: mock Kenyan driving licence (holder, licence no, ID, mobile). |

### 3. Roles (for demos)

- **Reviewer:** Can **Scan** and **Verify**. Cannot Protect or use Admin Ops.
- **Officer:** Can Scan, **Protect**, and Verify. No Admin Ops.
- **Admin:** Full access: Scan, Protect, Verify, **Admin Ops** (export audit, retention, OCR diagnostics, Sharp OCR toggle).

Use **admin** to show all features; use **reviewer** to show scan + verify only.

---

## Feature 1 — Scan (detect sensitive data)

**What it does:** Extracts text from the file (including OCR for images/PDFs), detects National IDs, phone numbers, emails, and KRA PINs, and shows a risk score plus recommended action.

**How to demonstrate:**

1. Go to the **Workflow** section (or use the “Guided Scan Flow” card).
2. **Upload a file:** click the file input or drag and drop one of:
   - `demo_docs/school_admission_sample.txt`
   - `demo_docs/sensitive_demo.pdf`
   - `demo_docs/kenyan_id_sample.jpg`
3. Click **Scan**.

**Point out:**

- **Risk score** (e.g. out of 100).
- **Risk insights** (short summary).
- **Top Critical Findings** — each finding with type (e.g. national_id, phone, email, kra_pin) and severity (High/Medium/Low).
- **Recommended action** (e.g. “Redact” or “Encrypt”) and the **Apply** button (optional).
- **Extracted text preview** — for images/PDFs this shows that OCR ran.
- **Processing timeline** — Upload → Extracting → Detecting → Classifying → Completed.

**Suggested script:**  
“We upload a document — text, PDF, or image. PrivGuard extracts text, runs OCR if needed, then detects Kenyan National IDs, phones, emails, and KRA PINs and assigns a risk score. The recommended action tells us the next step.”

---

## Feature 2 — Protect: Redact

**What it does:** Replaces every detected sensitive value with `[REDACTED]`. One-way; the original text cannot be recovered. The redacted file downloads automatically.

**How to demonstrate:**

1. In **Workflow**, open **Advanced Protection Options**.
2. Choose **Protect File:** e.g. `demo_docs/school_admission_sample.txt`.
3. Set **Protection Action** to **Redact**.
4. Click **Protect**.

**Point out:**

- **Protection Results:** Action = Redact, output file path.
- **Redaction quality:** PASS/FAIL, coverage %, leak count (should be 0 for a good redaction).
- **Preview** of redacted text (sensitive parts replaced by `[REDACTED]`).
- **“Redacted file has been downloaded”** and the **“Verify this redaction”** button.

**Suggested script:**  
“Redact permanently replaces sensitive data with [REDACTED]. The file downloads automatically. We can then use ‘Verify this redaction’ to confirm nothing leaked.”

---

## Feature 3 — Protect: Encrypt

**What it does:** Encrypts the full document with a one-time key (Fernet). You get an encrypted file and a separate key file. Only someone with the key can decrypt (via CLI).

**How to demonstrate:**

1. In **Advanced Protection Options**, choose **Protect File:** e.g. `demo_docs/sme_payroll_sample.txt`.
2. Set **Protection Action** to **Encrypt**.
3. Click **Protect**.

**Point out:**

- **Protection Results:** Action = Encrypt, output file and **key file** paths.
- **Preview** — first ~220 characters of the encrypted token (base64).
- **“Encrypted file has been downloaded”** and the **“Download key file”** button.
- The note: *Keep the key secure. To decrypt: `python main.py decrypt --input <.encrypted.txt> --key-path <.key> --output-dir outputs`*.

**Optional CLI decrypt (to prove it works):**

```powershell
cd C:\Users\HP\Desktop\privguard-ai
python main.py decrypt --input outputs/sme_payroll_sample.encrypted.txt --key-path keys/sme_payroll_sample.key --output-dir outputs
```

Then open `outputs/sme_payroll_sample.encrypted.decrypted.txt` and show it matches the original.

**Suggested script:**  
“Encrypt gives a protected file and a key file. We download both. Only with the key can we decrypt later via the CLI — useful for reversible protection.”

---

## Feature 4 — Verify redaction quality

**What it does:** Compares the **original** document with the **protected** (redacted) version and reports whether any of the original sensitive values still appear (leaks). Shows PASS/FAIL, coverage %, and a table of any leaked items.

**How to demonstrate:**

1. After a **Redact** run, click **“Verify this redaction”** (scrolls to the Verify section and hints at the file to use).
2. **Original File:** the file you redacted (e.g. `school_admission_sample.txt`).
3. **Protected File:** the redacted file you downloaded (e.g. `school_admission_sample.redacted.txt`).
4. Click **Verify**.

**Point out:**

- **Status:** PASS (no leaks) or FAIL (with leak count).
- **Coverage** and **Leaks** (e.g. 0 leaks).
- If FAIL: the table of leaked items (type and value).

**Suggested script:**  
“We upload the original and the redacted file. PrivGuard checks that none of the original sensitive values still appear. PASS means the redaction is good; FAIL and the table show what leaked.”

---

## Feature 5 — Processing timeline

**What it does:** Shows the current step (Upload → Extracting → Detecting → Classifying → Completed) and a progress bar during scan/protect/verify.

**How to demonstrate:**

- Run any **Scan** or **Protect** and watch the **Processing Timeline** card update in real time.

**Suggested script:**  
“The timeline shows each stage of processing so users see progress instead of a black box.”

---

## Feature 6 — KPIs and analytics

**What it does:** Top cards show **Documents Scanned**, **Average Risk Score**, **High Risk Ratio**, and **Sensitive Items** (IDs, phones, emails, KRA PINs) over recent activity. **Risk Overview Charts** show a donut and trend; **Risk Distribution** bars show High/Medium/Low counts; **Entity counts** break down by type.

**How to demonstrate:**

1. Run **several scans** with different demo files (e.g. school admission, SME payroll, PDF, ID image).
2. Click **Analytics** in the nav (or scroll to **Risk Overview Charts** and **Risk Distribution**).

**Point out:**

- KPI cards updating after each scan.
- Donut and trend charts.
- Risk distribution bars (High / Medium / Low).
- Entity breakdown (national IDs, phones, emails, KRA PINs).

**Suggested script:**  
“After a few scans, the dashboard summarizes how many documents we’ve scanned, average risk, and the mix of sensitive data types — useful for compliance and oversight.”

---

## Feature 7 — Recent scans

**What it does:** Lists the last scans (e.g. filename, risk score, time) so you can see recent activity at a glance.

**How to demonstrate:**

- After running scans, click **Recent Scans** in the nav or scroll to that card. The list updates with each new scan.

**Suggested script:**  
“Recent scans give a quick audit trail of what was scanned and the risk at a glance.”

---

## Feature 8 — Admin: Sharp OCR toggle

**What it does:** When **on**, OCR uses a stronger pipeline (upscale, denoise, sharpen, binarize) for blurry or unclear photos. When **off**, it uses simple grayscale + contrast. The choice is saved and applies to all users.

**How to demonstrate (admin only):**

1. Click **Admin Ops** in the nav.
2. Find the **Sharp OCR** toggle and the short description (“Better for blurry or unclear photos”).
3. Turn it **on** or **off** and point out the “Saved” feedback.

**Suggested script:**  
“Admins can turn Sharp OCR on for difficult images or off for faster, lighter processing. The setting is saved for the whole system.”

---

## Feature 9 — Admin: Export signed audit

**What it does:** Exports a signed JSON file of recent audit events (who scanned/protected what, when) plus a signature file so the log can be checked for tampering. Used for compliance and evidence.

**How to demonstrate (admin only):**

1. In **Admin Ops**, click **Export Signed Audit**.
2. Point out the result: e.g. “Signed audit export completed”, record count, file path.

**Suggested script:**  
“Export gives a signed audit trail for regulators or internal review. The signature lets anyone verify the log wasn’t altered.”

---

## Feature 10 — Admin: Run retention cleanup

**What it does:** Deletes old files in `uploads`, `outputs`, and `keys`, and old audit/scan events in the database, according to the retention policy in config (e.g. 30 days for files, 90 for audit).

**How to demonstrate (admin only):**

1. In **Admin Ops**, click **Run Retention Cleanup**.
2. Point out the result: e.g. “Retention cleanup completed”, deleted/kept counts.

**Suggested script:**  
“Retention cleanup enforces our data-minimization policy by removing old uploads and logs so we don’t keep data longer than needed.”

---

## Feature 11 — Admin: OCR diagnostics

**What it does:** Checks whether Tesseract OCR is installed and available. Needed for image and scanned-PDF text extraction.

**How to demonstrate (admin only):**

1. In **Admin Ops**, click **OCR Diagnostics**.
2. Point out **READY** (Tesseract available) or **ISSUE** (not installed or not in PATH).

**Suggested script:**  
“OCR diagnostics confirm the server can read text from images and scanned PDFs. If it fails, we know to install or fix Tesseract.”

---

## Feature 12 — Profile (optional)

**What it does:** Lets the user set a display name and avatar. Shown in the header.

**How to demonstrate:**

- Open the profile area (e.g. avatar/name in the header), edit display name and/or upload an image, save. Show the updated header.

---

## Feature 13 — Theme (light/dark)

**What it does:** Toggles light/dark theme; preference can be stored in the browser.

**How to demonstrate:**

- Use the theme toggle (if present) and show the dashboard switching between light and dark.

---

## Quick demo order (full run)

1. **Start app** → open dashboard, log in as **admin**.
2. **Scan** `demo_docs/school_admission_sample.txt` → show risk, findings, recommendation.
3. **Protect → Redact** the same file → show download and “Verify this redaction”.
4. **Verify** with original + redacted file → show PASS.
5. **Protect → Encrypt** `demo_docs/sme_payroll_sample.txt` → show encrypted file + key download and decrypt note.
6. **Scan** `demo_docs/kenyan_id_sample.jpg` (or `sensitive_demo.pdf`) → show OCR + detection.
7. **Admin Ops:** Sharp OCR toggle → Export Signed Audit → OCR Diagnostics → (optional) Retention Cleanup.
8. **Analytics / Recent Scans** → show KPIs and recent activity.

---

## CLI-only features (optional to mention)

- **Scan:**  
  `python main.py scan --input demo_docs/school_admission_sample.txt`
- **Protect (redact/encrypt):**  
  `python main.py protect --input demo_docs/school_admission_sample.txt --action redact --output-dir outputs`  
  `python main.py protect --input demo_docs/school_admission_sample.txt --action encrypt --output-dir outputs`
- **Decrypt:**  
  `python main.py decrypt --input outputs/<name>.encrypted.txt --key-path keys/<name>.key --output-dir outputs`
- **Verify redaction:**  
  `python main.py verify-redaction --original demo_docs/school_admission_sample.txt --protected outputs/school_admission_sample.redacted.txt`

These support scripting and server use; the dashboard is for interactive demos.

---

## Summary table

| Feature | Where | Demo data idea |
|--------|--------|-----------------|
| Scan | Workflow | Any of the 5 demo files |
| Protect → Redact | Workflow → Advanced | `.txt` or `.pdf` |
| Protect → Encrypt | Workflow → Advanced | `.txt` |
| Verify redaction | Verify section | Original + redacted file from step above |
| Timeline | Shown during scan/protect | Any scan/protect |
| KPIs & charts | Analytics / top cards | Run 2–3 scans first |
| Recent scans | Recent Scans card | After a few scans |
| Sharp OCR | Admin Ops (admin) | Toggle on/off |
| Export audit | Admin Ops (admin) | Click button |
| Retention cleanup | Admin Ops (admin) | Click button |
| OCR diagnostics | Admin Ops (admin) | Click button |

All demo data in `demo_docs/` is **synthetic**; safe to use in presentations and screenshots.
