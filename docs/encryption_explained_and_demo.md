# How encryption works in PrivGuard AI (and how to demo it)

## How it works

### Algorithm

- PrivGuard uses **symmetric encryption**: the same secret key is used to encrypt and decrypt.
- The implementation uses **Fernet** from the `cryptography` library:
  - **AES-128 in CBC mode** for confidentiality.
  - **HMAC-SHA256** for integrity (tampering is detected on decrypt).
  - The result is encoded as a **URL-safe base64** string (one token per document).

So: **one key** encrypts the whole document text; only someone with that key can decrypt it and get the original text back.

### What gets created when you encrypt

1. **Encrypted file** (e.g. `outputs/mydoc.encrypted.txt`)
   - Contains a single Fernet token: the entire document text, encrypted.
   - Safe to store or share only if the key is kept separate and secure.

2. **Key file** (e.g. `keys/mydoc.key`)
   - Contains the raw Fernet key (bytes).
   - **Whoever has this file can decrypt the document.** Store it securely and do not share it with the encrypted file.

### Flow in code

- **Key generation:** `Fernet.generate_key()` → new random key per encryption.
- **Encrypt:** `Fernet(key).encrypt(text.encode("utf-8"))` → ciphertext (then saved to `.encrypted.txt`).
- **Decrypt:** `Fernet(key).decrypt(token)` → original text (only with the correct key).

Decryption is **reversible**: with the right key you get the exact original text. That differs from **redaction**, which is one-way (you cannot recover the redacted values).

---

## Demo 1: Encrypt and decrypt from the CLI

Use a small text file (e.g. the demo doc). Run from the **project root** (`C:\Users\HP\Desktop\privguard-ai`).

### Step 1 – Encrypt

```powershell
cd C:\Users\HP\Desktop\privguard-ai
python main.py protect --input demo_docs/school_admission_sample.txt --action encrypt --output-dir outputs
```

**What happens:**

- The app reads the file, extracts text, generates a **new key**, and:
  - Writes the encrypted text to `outputs/school_admission_sample.encrypted.txt`
  - Writes the key to `outputs/school_admission_sample.key` (same directory as the encrypted file when using default `--output-dir outputs`)

**Show:**

- Open `outputs/school_admission_sample.encrypted.txt`: you see one long line of base64 (the Fernet token), not the original text.
- Point out that `outputs/school_admission_sample.key` exists and is required for decryption.

### Step 2 – Decrypt

```powershell
python main.py decrypt --input outputs/school_admission_sample.encrypted.txt --key-path outputs/school_admission_sample.key --output-dir outputs
```

**What happens:**

- The app reads the encrypted file (one token), loads the key from `keys/school_admission_sample.key`, decrypts, and writes plain text to e.g. `outputs/school_admission_sample.decrypted.txt`.

**Show:**

- Open `outputs/school_admission_sample.decrypted.txt`: content should match the original file.

### Step 3 – Wrong key (optional)

```powershell
python main.py decrypt --input outputs/school_admission_sample.encrypted.txt --key-path keys/some_other.key --output-dir outputs
```

If `some_other.key` is different, decryption fails (invalid key/token). That shows that only the correct key can recover the data.

---

## Demo 2: Encrypt from the dashboard

1. Log in to the dashboard (e.g. http://127.0.0.1:5000).
2. Open the **Protect** section.
3. Choose a file (e.g. `demo_docs/school_admission_sample.txt`).
4. Set action to **Encrypt**.
5. Click **Protect**.

**What you see:**

- A message that encryption succeeded.
- **Output file:** `outputs/<stem>.encrypted.txt` (e.g. `school_admission_sample.encrypted.txt`).
- **Key file:** `keys/<stem>.key` (e.g. `school_admission_sample.key`).
- A short **preview** of the encrypted token (first 220 characters).

**To decrypt after using the dashboard:**

- The encrypted file is in `outputs/` (e.g. `outputs/school_admission_sample.encrypted.txt`). The key is in `keys/` (e.g. `keys/school_admission_sample.key`) on the server. Use the same CLI decrypt command with those two paths, e.g. `--input outputs/...encrypted.txt --key-path keys/...key --output-dir outputs`.

---

## One-line summary

**Encryption** = one secret key per document; the key is stored in a `.key` file and the ciphertext in an `.encrypted.txt` file. Only with that key can you run **decrypt** (CLI) and get the original text back.
