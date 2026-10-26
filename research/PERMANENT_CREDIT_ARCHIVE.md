# Permanent encrypted HY/IG observation archive

A separate *encrypted, durable* observation store prevents expiry of the 5-year public dashboard history. It only adds previously unseen dated observations, never removes dates and does not silently overwrite earlier values. The existing `history_5y.ndjson` remains unchanged.

## How storage works

- `scripts/archive_credit_permanent.py` downloads currently accessible FRED HY/IG credit observations.
- The process decrypts any existing encrypted archive, merges new dated observations without deleting old ones, and atomically replaces it with an authenticated Fernet-encrypted archive.
- GitHub Actions commits only `research/private_data/credit_archive.fernet` to the repository. It does **not** commit raw observations or expose them in Pages.
- The encryption key lives solely in the GitHub Actions repository secret `CREDIT_ARCHIVE_KEY`. It **must be backed up privately by the repository owner**: losing or rotating the key without re-encrypting makes all previously stored history unrecoverable.
- The source may have data/redistribution restrictions. Encryption is a technical privacy control, **not** permission to retain, reuse or redistribute licensed index datasets. Check the relevant contractual terms and, if retention is restricted, disable this archive.

## One-time setup

1. Generate a new random Fernet key locally (not in this chat):
   `python3 -c "import base64,secrets;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`
2. Add it to GitHub repository Settings → Secrets and variables → Actions as `CREDIT_ARCHIVE_KEY`. Never commit or paste this key into issues or messages.
3. Keep a private offline backup of the key in a password manager.
4. Once the workflow reaches the default branch, manually run **Permanent encrypted credit archive** once to initialise it; verify green success and an encrypted file commit.
5. The owner has confirmed that the site is intended solely for personal research. The workflow is configured to run daily at 07:45 UTC once merged; the archive stays encrypted and is not served through Cloudflare Pages. Review the data-provider terms as appropriate for continued private retention.

## Safeguards and limits

- Archive initialisation starts with whatever history FRED still exposes (currently approximately three years). This implementation does not recreate observations no longer available through FRED.
- Historic rows already saved are never deleted by the archiver, even if the FRED 3-year window advances.
- An API failure for one series preserves its prior values. Failures for both series abort without modifying the encrypted file.
- Data snapshots are captured when first encountered; they are **not a complete revision/vintage history**, and FRED observations can have publication lags.
- Public dashboard history and historical research calculations do not change in this release.
- Encrypting data inside a public Git repo hides ordinary contents but also preserves ciphertext in public Git history. Access control using a dedicated private repository or private object storage would offer stronger governance if future needs warrant it.

## Licensing hold (October 2026)

The source FRED series identify ICE Data Indices as the copyright owner; ICE terms restrict external publication/redistribution and FRED API terms preserve third-party restrictions. Before expanding access or publishing data, seek written clarification covering *ongoing private storage of dated observations*, any necessary permitted retention after FRED's rolling window removes older dates, *derived public statistics*, and optional AI-assisted interpretation. Encryption is not a substitute for permission.
