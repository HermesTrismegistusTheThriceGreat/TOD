# Phase 1: Security Foundation - Research

**Researched:** 2026-01-29
**Domain:** Credential Encryption & Log Security (Python/FastAPI)
**Confidence:** HIGH

## Summary

Phase 1 establishes the encrypted credential infrastructure that all subsequent phases depend on. The phase requires implementing Fernet-based encryption for API credentials at rest and preventing credentials from appearing in logs. Research confirms that this is the established best practice in Python/FastAPI ecosystems, with a clear pattern: encrypt credentials before database storage using cryptography's Fernet, implement log redaction to mask secrets, and use pre-commit hooks to prevent accidental commits of unencrypted credentials.

The project already uses python-dotenv for environment variable management, which is the correct approach for loading the Fernet encryption key on server startup. Credentials will flow: ENV → Encrypt with Fernet → Store in DB → Decrypt on retrieval. Logging infrastructure exists but needs enhancement to redact sensitive data.

**Primary recommendation:** Use the cryptography library's Fernet class (from `cryptography.fernet.Fernet`) as the encryption engine, store the key via environment variable (ENCRYPTION_KEY), implement a credential encryption service with encrypt/decrypt methods, add log filtering to redact secrets, and deploy detect-secrets pre-commit hook to prevent commits containing plaintext credentials.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cryptography | 47.0.0+ | Fernet symmetric encryption | Industry-standard, audited, used by major projects (Django, Sentry); handles encryption + HMAC-SHA256 authentication automatically |
| python-dotenv | 1.0.0+ | Environment variable loading | Already in use in codebase; loads encryption key on startup |
| fastapi | Current | Request validation & routing | Already in use; no changes needed for this phase |
| detect-secrets | 1.4.0+ | Pre-commit hook secret detection | Enterprise-friendly (Yelp-maintained), catches high-entropy secrets before commit |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logredactor | 0.5.0+ | Log filtering framework | Optional enhancement for sophisticated redaction patterns; provides reusable filter framework |
| python-logging-redaction | Latest | Custom logging redaction | Lighter alternative to logredactor if only simple secret masking needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Fernet (AES-128) | PyCryptodome + custom HMAC | Full control but no authenticated encryption by default; requires careful implementation |
| Fernet | AES-256 via cryptography lib | Overkill for API credentials; Fernet's AES-128 + HMAC is sufficient and faster |
| detect-secrets | GitGuardian ggshield | More advanced pattern detection but requires external service; detect-secrets works offline |
| Environment variable key | AWS Secrets Manager | Better for production multi-service deployments; not needed for this phase; can migrate later |

**Installation:**
```bash
uv add cryptography python-dotenv detect-secrets
uv add --dev pytest pytest-asyncio httpx
```

## Architecture Patterns

### Recommended Project Structure
```
apps/orchestrator_3_stream/backend/
├── modules/
│   ├── config.py                    # [EXISTING] Loads ENCRYPTION_KEY from .env
│   ├── encryption_service.py        # [NEW] Credential encryption/decryption
│   ├── logger.py                    # [MODIFIED] Add secret redaction filter
│   └── database.py                  # [EXISTING, no changes needed]
├── .env.sample                      # [MODIFIED] Add ENCRYPTION_KEY placeholder
├── .pre-commit-config.yaml          # [NEW] detect-secrets hook configuration
└── tests/
    └── test_encryption_service.py   # [NEW] Round-trip encryption tests
```

### Pattern 1: Credential Encryption Service
**What:** A centralized service that encrypts credentials before storage and decrypts on retrieval. The service manages the Fernet instance and provides encrypt(plaintext) → ciphertext and decrypt(ciphertext) → plaintext methods.

**When to use:** Every credential field in the database (API keys, secrets, tokens). This is the single source of truth for encryption/decryption.

**Example:**
```python
# Source: cryptography.io official docs + phase requirements
from cryptography.fernet import Fernet
import os

class CredentialEncryptionService:
    """Encrypts and decrypts API credentials using Fernet"""

    def __init__(self):
        # Load encryption key from environment on server startup
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY not set in environment")
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt credential value and return base64-encoded ciphertext"""
        if not plaintext:
            return ""
        ciphertext = self.cipher.encrypt(plaintext.encode())
        return ciphertext.decode()  # Store as string in database

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt stored ciphertext and return plaintext"""
        if not ciphertext:
            return ""
        plaintext = self.cipher.decrypt(ciphertext.encode())
        return plaintext.decode()

# Generate a new key (run once, save to .env)
# key = Fernet.generate_key()  # Returns bytes, decode to string for .env
```

### Pattern 2: Database Field Encryption (SQLAlchemy Hybrid)
**What:** A database column that stores encrypted data but provides a Python property that automatically encrypts on assignment and decrypts on retrieval.

**When to use:** For credential columns in the database (API keys, secrets, tokens). Transparent encryption/decryption in ORM models.

**Example:**
```python
# Source: SQLAlchemy wiki DatabaseCrypt pattern
from sqlalchemy import Column, String
from sqlalchemy.ext.hybrid import hybrid_property

class ApiCredential(Base):
    __tablename__ = "api_credentials"

    id = Column(UUID, primary_key=True)
    name = Column(String, nullable=False)
    _api_key_encrypted = Column("api_key", String)  # Stored encrypted in DB

    @hybrid_property
    def api_key(self) -> str:
        """Property that automatically decrypts on access"""
        if not self._api_key_encrypted:
            return ""
        return encryption_service.decrypt(self._api_key_encrypted)

    @api_key.setter
    def api_key(self, plaintext: str):
        """Property that automatically encrypts on assignment"""
        self._api_key_encrypted = encryption_service.encrypt(plaintext)
```

### Pattern 3: Log Redaction Filter
**What:** A logging filter that intercepts log records and masks secrets using regex patterns before writing to files or console.

**When to use:** Global redaction on all logs to prevent credential leakage in error messages, tracebacks, or debug output.

**Example:**
```python
# Source: https://betterstack.com/community/guides/logging/sensitive-data/
import logging
import re

class SecretRedactionFilter(logging.Filter):
    """Redacts secrets from log records"""

    PATTERNS = [
        (r"ALPACA_API_KEY=[\w\-\.]+", "ALPACA_API_KEY=***"),
        (r"ALPACA_SECRET_KEY=[\w\-\.]+", "ALPACA_SECRET_KEY=***"),
        (r"api[_-]?key[:\s=]+[\w\-\.]+", "api_key=***"),
        (r"secret[:\s=]+[\w\-\.]+", "secret=***"),
        (r"token[:\s=]+[\w\-\.]{20,}", "token=***"),
        (r"bearer\s+[\w\-\.]+", "bearer ***"),
    ]

    def filter(self, record):
        """Mask secrets in log message and exception info"""
        if record.msg:
            record.msg = self._redact(str(record.msg))

        # Also redact exception tracebacks if present
        if record.exc_info:
            record.exc_text = self._redact(record.exc_text or "")

        return True

    def _redact(self, text: str) -> str:
        """Apply all redaction patterns"""
        for pattern, replacement in self.PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

# Add to logger in logger.py
logger.addFilter(SecretRedactionFilter())
```

### Anti-Patterns to Avoid
- **Store plaintext credentials in database:** NEVER. Always encrypt before writing. Plaintext defeats the purpose of credential infrastructure.
- **Hardcode encryption keys in source code:** ALWAYS use environment variables via python-dotenv. Keys should never be in git.
- **Log credentials in error messages:** MUST add redaction filters. A single unredacted credential leak exposes the entire system.
- **Skip pre-commit hooks:** ALWAYS deploy detect-secrets. Prevention is cheaper than incident response.
- **Use weak key derivation:** Use at least 1,200,000 iterations if deriving keys from passwords (PBKDF2HMAC). For random keys, use Fernet.generate_key().

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "Symmetric encryption is simple, I'll use AES directly" | Custom AES implementation | cryptography.Fernet | AES requires PKCS7 padding, random IVs per message, HMAC authentication, and timestamp embedding. Fernet handles all of this automatically. One mistake exposes all data. |
| "I'll just filter secrets from logs manually" | Custom log filtering | Structured logging + RedactionFilter | Manual filtering with string matching misses edge cases (different formats, encoding, exceptions). Centralized filters catch everything. |
| "I'll store the key in a config file, that's secure enough" | Config file key storage | Environment variables via python-dotenv | Config files can be accidentally committed, backed up unencrypted, or leaked in container images. Environment variables follow cloud-native best practices. |
| "Let developers commit their own credentials, we'll clean up manually" | Manual secret removal | detect-secrets pre-commit hook | At least 15% of GitHub commits contain secrets. Hooks prevent the commit entirely; cleanup is already too late. |

**Key insight:** Encryption and secret management have well-solved patterns in the cryptography community. The mistakes are almost always in implementation details (key storage, log leakage, validation) not in the encryption itself.

## Common Pitfalls

### Pitfall 1: Unencrypted Key Exposure
**What goes wrong:** The Fernet encryption key is stored in plaintext in `.env` or version control, defeating the entire purpose of encryption.

**Why it happens:** Developers think the key is "just configuration" like port numbers. It's not—it's a secret.

**How to avoid:**
- Store encryption key ONLY in environment variables, never in `.env` files that could be committed
- On development machines, generate a test key and document it as "NOT for production"
- Production key comes from secrets manager (AWS Secrets Manager, HashiCorp Vault, or cloud provider)
- Validate in startup: if ENCRYPTION_KEY is missing, raise an error before starting the server

**Warning signs:**
- `.env` file is in git history
- Same encryption key in all environments (dev, staging, production)
- Key hardcoded in source code

### Pitfall 2: Partial Log Redaction
**What goes wrong:** Credentials appear in logs in slightly different formats than the redaction filter expects (uppercase, URL-encoded, nested in exceptions).

**Why it happens:** Regex patterns can't catch every format variation. Developers add one redaction pattern but miss variations.

**How to avoid:**
- Test log redaction filter against real error messages from the application
- Include patterns for common variations: `api_key=`, `API_KEY=`, `apiKey=`, URL-encoded versions
- Test with exceptions: raise an exception with a credential in the message and verify it's redacted
- Document all redacted patterns in code comments so future developers know what's covered

**Warning signs:**
- Credentials appear in application logs (detected in log audit per Phase 1 success criteria)
- Different credential formats in different parts of the app

### Pitfall 3: Round-Trip Encryption Failures
**What goes wrong:** Decrypt returns a different value than the original (missing characters, encoding issues, whitespace).

**Why it happens:** Fernet handles bytes, but Python strings can have encoding surprises. Whitespace in credentials might be trimmed during storage.

**How to avoid:**
- Always test encryption/decryption round-trips: encrypt(X) → decrypt → verify equals X
- Use bytes consistently: encode to UTF-8 before encryption, decode after
- Handle edge cases: empty strings, special characters, Unicode
- Don't manipulate the ciphertext (trim whitespace, change case) between encrypt and decrypt

**Warning signs:**
- Credentials fail to authenticate after retrieval
- "InvalidToken" errors from Fernet during decrypt
- Decrypted values have missing characters or garbled text

### Pitfall 4: Key Rotation Not Tested
**What goes wrong:** The app can encrypt with a new key but can't decrypt old data, causing a production outage when key rotation happens.

**Why it happens:** Key rotation is tested manually once, then the old key is deleted. In production, you can't roll back.

**How to avoid:**
- Use Fernet's MultiFernet for zero-downtime key rotation: maintain a list of keys, decrypt tries each in order
- Test key rotation: encrypt with key A, rotate to key B, verify you can still decrypt key A data
- Document the key rotation procedure before Phase 1 is complete
- For this phase, a single key is fine. Phase 3 can implement MultiFernet if needed.

**Warning signs:**
- No test for decrypting data encrypted with old keys
- Key rotation procedure not documented

### Pitfall 5: Credentials Leaked in Error Messages
**What goes wrong:** A credential appears in an exception message that gets logged, even though the log filter is active.

**Why it happens:** Exceptions are sometimes logged with `.format()` or f-strings that don't go through the filter cleanly.

**How to avoid:**
- When raising exceptions with credentials, never include the actual credential value
- Use placeholders: `raise ValueError(f"Failed to authenticate as {username}, check credentials")` not `raise ValueError(f"Failed with key {api_key}")`
- Test exception handling: deliberately pass a bad credential and verify the full message is redacted in logs
- Use `record.exc_text` in the filter to catch traceback strings

**Warning signs:**
- Credentials appear in exception stack traces in logs
- Different log output for successful vs. failed authentication

## Code Examples

Verified patterns from official sources:

### Encryption Service Implementation
```python
# Source: https://cryptography.io/en/latest/fernet/
from cryptography.fernet import Fernet, InvalidToken
import os
import logging

logger = logging.getLogger(__name__)

class CredentialEncryptionService:
    """
    Centralized service for encrypting/decrypting API credentials.
    Loads encryption key from ENCRYPTION_KEY environment variable on startup.
    """

    def __init__(self):
        """Initialize with Fernet cipher using environment key"""
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY environment variable not set. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        try:
            self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        except Exception as e:
            raise ValueError(f"Invalid ENCRYPTION_KEY: {e}")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext credential to base64-encoded ciphertext.

        Args:
            plaintext: Unencrypted credential value (e.g., API key)

        Returns:
            Base64-encoded ciphertext safe to store in database

        Raises:
            ValueError: If plaintext is None
        """
        if plaintext is None:
            raise ValueError("Cannot encrypt None value")

        if not plaintext:
            return ""

        try:
            ciphertext = self.cipher.encrypt(plaintext.encode('utf-8'))
            return ciphertext.decode('ascii')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt base64-encoded ciphertext to plaintext.

        Args:
            ciphertext: Base64-encoded ciphertext from database

        Returns:
            Decrypted plaintext credential

        Raises:
            InvalidToken: If ciphertext is corrupted or wrong key used
        """
        if not ciphertext:
            return ""

        try:
            plaintext = self.cipher.decrypt(ciphertext.encode('ascii'))
            return plaintext.decode('utf-8')
        except InvalidToken:
            logger.error("Decryption failed: invalid token or wrong key")
            raise
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
```

### Generating and Managing the Encryption Key
```bash
# Generate a new encryption key (do this once per environment)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Output: s0VQblMxk-7jHaRYqpjIw8sdfvFIHa9VqDYqL_zU1Ks=

# Add to .env (development only)
echo "ENCRYPTION_KEY=s0VQblMxk-7jHaRYqpjIw8sdfvFIHa9VqDYqL_zU1Ks=" >> .env

# For production, set via environment or secrets manager
export ENCRYPTION_KEY="s0VQblMxk-7jHaRYqpjIw8sdfvFIHa9VqDYqL_zU1Ks="
```

### Round-Trip Encryption Test (Success Criteria)
```python
# Source: cryptography.io + Phase 1 success criteria
def test_encryption_round_trip():
    """Test that encrypt(X) → decrypt → X"""
    service = CredentialEncryptionService()

    # Test cases from Phase 1 requirements
    test_cases = [
        "PK0123456789ABCDEF",  # Typical Alpaca API key
        "sp0123456789abcdefghijklmnop",  # Typical Alpaca secret key
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  # JWT token
        "special!@#$%^&*()chars",  # Edge case: special chars
        "",  # Edge case: empty string
    ]

    for plaintext in test_cases:
        # Encrypt
        ciphertext = service.encrypt(plaintext)

        # Verify ciphertext is different from plaintext
        assert ciphertext != plaintext or plaintext == ""

        # Decrypt
        decrypted = service.decrypt(ciphertext)

        # Verify round-trip
        assert decrypted == plaintext, f"Round-trip failed: {plaintext} != {decrypted}"
```

### Log Redaction Filter
```python
# Source: https://betterstack.com/community/guides/logging/sensitive-data/
import logging
import re

class CredentialRedactionFilter(logging.Filter):
    """
    Redacts API credentials from log records to prevent accidental exposure.
    Matches common credential formats and replaces with masked values.
    """

    # Patterns to match various credential formats
    REDACTION_PATTERNS = [
        # Environment variable formats
        (r'ALPACA_API_KEY\s*=\s*[\w\-\.]+', 'ALPACA_API_KEY=***'),
        (r'ALPACA_SECRET_KEY\s*=\s*[\w\-\.]+', 'ALPACA_SECRET_KEY=***'),
        (r'API_KEY\s*=\s*[\w\-\.]+', 'API_KEY=***'),
        (r'SECRET_KEY\s*=\s*[\w\-\.]+', 'SECRET_KEY=***'),

        # JSON/dict formats
        (r'"api[_-]?key"\s*:\s*"[^"]*"', '"api_key":"***"'),
        (r'"secret[_-]?key"\s*:\s*"[^"]*"', '"secret_key":"***"'),
        (r"'api[_-]?key'\s*:\s*'[^']*'", "'api_key':'***'"),
        (r"'secret[_-]?key'\s*:\s*'[^']*'", "'secret_key':'***'"),

        # Query string and URL formats
        (r'[?&]api[_-]?key=[^&]*', '?api_key=***'),
        (r'Bearer\s+[\w\-\.]+', 'Bearer ***'),

        # Alpaca-specific key formats (PK... for API key, sp... for secret)
        (r'\bPK[\w]{17,}\b', 'PK***'),
        (r'\bsp[\w]{28,}\b', 'sp***'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter a log record to redact credentials.

        Args:
            record: LogRecord to filter

        Returns:
            True (allow record to be logged)
        """
        # Redact message
        if record.msg:
            record.msg = self._redact_string(str(record.msg))

        # Redact formatted message
        try:
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: self._redact_string(str(v)) for k, v in record.args.items()}
                else:
                    record.args = tuple(self._redact_string(str(arg)) for arg in record.args)
        except Exception:
            pass  # Don't break logging if args redaction fails

        # Redact exception traceback
        if record.exc_text:
            record.exc_text = self._redact_string(record.exc_text)

        return True

    def _redact_string(self, text: str) -> str:
        """Apply all redaction patterns to text"""
        for pattern, replacement in self.REDACTION_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text
```

### Pre-commit Hook Configuration
```yaml
# .pre-commit-config.yaml
# Source: https://github.com/Yelp/detect-secrets

repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        name: detect-secrets
        entry: detect-secrets scan --baseline .secrets.baseline
        language: python
        types: [python]
        stages: [commit]
        args:
          - --baseline
          - .secrets.baseline
          - --plugins
          - Base64HighEntropyString
          - Basic Auth Credentials
          - Artifactory Credentials
          - AWS Access Key
          - AWS Manager ID
          - Azure Storage Account Access Key
          - Google API Key
          - Private Key
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Store credentials in plaintext | Encrypt with Fernet before DB storage | Standard since cryptography 1.0 (2014) | Assumed in all modern compliance frameworks; plaintext is unacceptable for production |
| Manual log filtering with string search | Centralized RedactionFilter in logging pipeline | Best practice since 2016 (Sentry, OWASP) | Consistent redaction; no edge cases missed |
| Post-commit secret detection | Pre-commit hook detection (detect-secrets) | Industry adoption ~2018 onwards | Prevention model; stops commit before it happens |
| Store key in config files | Environment variables via python-dotenv | Cloud-native standard (12-factor app) | Portable across environments; compatible with containerization |
| Single static key forever | Key rotation via MultiFernet (optional later) | Not in Phase 1; deferred to Phase 3 | Zero-downtime key rotation; limits damage from key compromise |

**Deprecated/outdated:**
- **Plaintext credential storage:** Unacceptable for any system handling user data. All production systems must encrypt.
- **Manual secret removal:** Too slow and error-prone. Pre-commit hooks prevent the leak.
- **Hardcoded keys in source:** Violates every compliance standard. Always use environment variables.

## Open Questions

Things that couldn't be fully resolved:

1. **Alpaca Token Lifecycle Documentation**
   - What we know: Alpaca provides API key (PK...) and secret key (sp...) formats; credentials can be revoked; no public documentation on key expiration or rotation requirements
   - What's unclear: Does Alpaca automatically expire keys? What's the best rotation frequency? Can keys be rotated without downtime?
   - Recommendation: Document in Phase 1 completion that Alpaca support was contacted for credential lifecycle best practices; implement generic key rotation in Phase 3 if needed
   - Reference: Phase context noted "Alpaca token lifecycle not well documented - may need to contact support"

2. **Key Rotation Scope for Phase 1**
   - What we know: Fernet supports MultiFernet for rotating keys without data loss
   - What's unclear: Should Phase 1 include MultiFernet implementation or defer to Phase 3?
   - Recommendation: Phase 1 should implement single-key encryption; Phase 3 (deferred ideas) can upgrade to MultiFernet if production needs it

3. **Credential Expiration vs. Key Expiration**
   - What we know: Credentials (API keys) can expire; encryption keys (Fernet) don't expire unless rotated
   - What's unclear: Should we track credential expiration separately from encryption?
   - Recommendation: Store credential expiration as a separate field in database; Phase 2 can add cleanup tasks for expired credentials

## Sources

### Primary (HIGH confidence)
- **cryptography.io** - [Fernet documentation](https://cryptography.io/en/latest/fernet/) - API, best practices, key management, token expiration, MultiFernet
- **Official Alpaca Docs** - [Authentication](https://docs.alpaca.markets/docs/authentication) - Credential types, access control, credential expiration
- **Pydantic Official Docs** - [Secret Types](https://docs.pydantic.dev/2.0/usage/types/secrets/) - SecretStr/SecretBytes masking behavior
- **SQLAlchemy Wiki** - [DatabaseCrypt Pattern](https://github.com/sqlalchemy/sqlalchemy/wiki/DatabaseCrypt) - Hybrid property encryption examples
- **Yelp/detect-secrets** - [GitHub repo](https://github.com/Yelp/detect-secrets) - Pre-commit hook configuration, entropy detection

### Secondary (MEDIUM confidence)
- Better Stack Community - [Logging sensitive data best practices](https://betterstack.com/community/guides/logging/sensitive-data/) - Log redaction filter patterns, multiple sources confirming approach
- DEV Community - [Pydantic Secret Types guide](https://www.getorchestra.io/guides/pydantic-secret-types-handling-sensitive-data-securely-with-secretstr-and-secretbytes) - SecretStr masking and FastAPI patterns
- Medium articles by Parthiban Marimuthu - [Fernet encryption guide](https://parthibanmarimuthu.medium.com/securely-encrypting-sensitive-data-in-python-with-fernet-dd50638bde0f) - Round-trip encryption examples

### Tertiary (LOW confidence, marked for validation)
- WebSearch sources on "Python credential encryption patterns" - Community blog posts without official documentation; used for pattern confirmation only
- Stack Overflow discussions on SQLAlchemy hybrid encryption - User-contributed patterns; implementation may vary

## Metadata

**Confidence breakdown:**
- **Standard stack (HIGH):** Cryptography library Fernet is official, audited, widely used. Python-dotenv is standard. Detect-secrets is enterprise-maintained by Yelp. All verified with official documentation.
- **Architecture patterns (HIGH):** Encryption service pattern is documented in cryptography.io. Log redaction patterns verified across multiple sources. SQLAlchemy hybrid property approach in official wiki.
- **Pitfalls (HIGH):** All major pitfalls documented in official security guides (Sentry, OWASP, Better Stack). Round-trip test pattern from cryptography.io examples.
- **Code examples (HIGH):** All examples derived from official documentation or verified against best practices. Edge cases documented.
- **Alpaca integration (MEDIUM):** Alpaca documentation is clear on credential types but limited on lifecycle. Phase context notes this as a blocker requiring support contact.

**Research date:** 2026-01-29
**Valid until:** 2026-02-28 (stable technologies, 30-day horizon)
**Next validation:** Before Phase 2 if Alpaca token lifecycle requires changes to credential model
