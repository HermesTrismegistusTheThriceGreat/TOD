# Technology Stack: Multi-Tenant Alpaca Trading Platform

**Project:** Alpaca Trading Platform with Multi-User Credential Management
**Researched:** 2026-01-29
**Focus:** Secure credential encryption, multi-tenant isolation, Alpaca API integration

## Executive Summary

This is a focused stack recommendation for **adding multi-tenant credential management** to an existing single-user Alpaca trading chat. The core stack (FastAPI, PostgreSQL/NeonDB, Vue 3) stays unchanged. The additions are:

- **Credential Encryption**: Python `cryptography` library with Fernet for symmetric encryption at rest
- **Multi-Tenant Isolation**: PostgreSQL Row-Level Security (RLS) with SQLAlchemy-tenants integration
- **Credential Storage**: Dedicated encrypted credentials table with user/account mapping
- **Alpaca Integration**: alpaca-py SDK with per-user credential management

This approach trades simplicity for security: credentials are encrypted in database, isolated per user via RLS, and accessed only when needed. No external vault required for this scale (under 1000 users).

---

## Recommended Stack

### Credential Management

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **cryptography** | 47.0.0+ | Fernet symmetric encryption for credentials at rest | Industry standard for Python encryption, actively maintained, provides authenticated encryption (confidentiality + integrity), suitable for application-level encryption. Alternatives like PyCryptodome are lower-level and require more manual key management. |
| **sqlalchemy-tenants** | 0.1.0+ | Multi-tenant data isolation with RLS | Seamlessly integrates PostgreSQL Row-Level Security with SQLAlchemy ORM, handles automatic tenant context in queries, eliminates manual tenant_id filtering bugs. Decorator-based approach is cleaner than manual RLS policy setup. |
| **SQLAlchemy** | 2.0+ (existing) | ORM for multi-tenant models | Already in stack; SQLAlchemy 2.0+ has strong support for TypeDecorators and custom column types for transparent encryption. TypeDecorator pattern allows encrypted fields to be defined inline on models. |

### Database Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **PostgreSQL / NeonDB** | 14+ / current | Multi-tenant database with RLS | PostgreSQL's Row-Level Security is battle-tested for multi-tenant SaaS. NeonDB (serverless Postgres) simplifies scaling without managing instances. RLS enforces isolation at database level, not application level—more secure. |
| **alembic** | 1.13+ (existing) | Schema migrations | Required for RLS policy setup and encrypted columns; existing migration framework should handle new multi-tenant tables. |

### API Credential Integration

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **alpaca-py** | 0.21.0+ | Official Alpaca SDK for trading APIs | Primary choice for Alpaca integration. Supports Broker API for multi-account management. Credential passing pattern is straightforward: `BrokerClient(api_key, secret_key)`. No special multi-tenant features—you manage that in your app. |
| **hvac** | 1.2.0+ | HashiCorp Vault client (optional) | Only if you scale beyond ~1000 users or need dynamic credential rotation. For initial multi-tenant launch, app-level encryption + database isolation is sufficient. Skip this unless you have compliance requirements. |

### Supporting Libraries (New Additions)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| **python-dotenv** | 1.0.0+ | Load encryption keys from environment | Essential: never hardcode the Fernet key. Load from `.env` locally, from secrets manager in production. |
| **pydantic** | 2.0+ (existing) | Validate credential schemas | Define CredentialModel for type safety; validate API key formats before storage. |

---

## Architecture: Credential Storage Pattern

### Core Approach

```
User (has many) -> UserAlpacaCredential (encrypted)
                         |
                    [tenant_id]
                    [api_key]      <- Encrypted with Fernet
                    [secret_key]   <- Encrypted with Fernet
                    [account_id]   <- Mapped to Alpaca account
                         |
                    RLS Policy
                    (user can only see own credentials)
```

### Database Schema

```sql
-- Credentials table with encryption + RLS
CREATE TABLE user_alpaca_credentials (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    tenant_id UUID NOT NULL,  -- From JWT or session context
    account_id TEXT,           -- Alpaca account identifier
    api_key_encrypted BYTEA NOT NULL,  -- Fernet encrypted
    secret_key_encrypted BYTEA NOT NULL,  -- Fernet encrypted
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    is_live BOOLEAN DEFAULT FALSE,  -- Paper vs live account
    UNIQUE(user_id, account_id)
);

-- Enable RLS
ALTER TABLE user_alpaca_credentials ENABLE ROW LEVEL SECURITY;

-- Policy: users see only their own credentials
CREATE POLICY user_credentials_isolation ON user_alpaca_credentials
    USING (user_id = current_user_id());  -- Function set in session context
```

### SQLAlchemy Model with Encryption

```python
from cryptography.fernet import Fernet
from sqlalchemy import Column, String, LargeBinary, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.hybrid import hybrid_property

class UserAlpacaCredential(Base):
    __tablename__ = "user_alpaca_credentials"
    __table_args__ = (
        Index("idx_user_account", "user_id", "account_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    tenant_id: Mapped[UUID] = mapped_column()
    account_id: Mapped[str]

    # Encrypted storage
    api_key_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    secret_key_encrypted: Mapped[bytes] = mapped_column(LargeBinary)

    # Instance methods for transparent encryption/decryption
    def set_api_key(self, plaintext: str) -> None:
        """Encrypt before storing"""
        key = os.environ.get("FERNET_KEY").encode()
        f = Fernet(key)
        self.api_key_encrypted = f.encrypt(plaintext.encode())

    def get_api_key(self) -> str:
        """Decrypt on access"""
        key = os.environ.get("FERNET_KEY").encode()
        f = Fernet(key)
        return f.decrypt(self.api_key_encrypted).decode()

    # Same for secret_key...
```

### Accessing Credentials Safely

```python
# FastAPI endpoint to fetch and use credentials
@app.get("/api/accounts/{account_id}/positions")
async def get_positions(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch user's credential (RLS ensures isolation)
    cred = await db.execute(
        select(UserAlpacaCredential).where(
            (UserAlpacaCredential.user_id == current_user.id) &
            (UserAlpacaCredential.account_id == account_id)
        )
    )
    credential = cred.scalar_one_or_none()

    if not credential:
        raise HTTPException(status_code=404)

    # Decrypt in memory, use, then discard
    api_key = credential.get_api_key()
    secret = credential.get_secret_key()

    broker = BrokerClient(api_key, secret)
    positions = await broker.get_positions()  # Or use asyncio wrapper

    # Decrypted keys are in memory only, never stored
    return positions
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| **Encryption Library** | cryptography + Fernet | PyCryptodome | Fernet provides built-in authenticated encryption (HMAC + AES), eliminating a class of bugs. PyCryptodome is lower-level and requires manual mode selection; more suited to specialized cryptography work. cryptography is the Python community standard. |
| **Encryption Library** | cryptography + Fernet | AWS KMS / HashiCorp Vault | Adds operational complexity (network calls, key management overhead). For MVP with <1000 users and single deployment, app-level encryption is sufficient. Revisit if: compliance requires key rotation, multiple deployment regions, or you scale to 10k+ users. |
| **Multi-Tenant Isolation** | PostgreSQL RLS + sqlalchemy-tenants | Application-level filtering (WHERE user_id = ?) | Database-level RLS is more secure—prevents accidental data leaks from query bugs. SQLAlchemy-tenants is a thin abstraction that automates RLS context; manual WHERE clauses are error-prone. |
| **Multi-Tenant Isolation** | Shared Schema (RLS) | Database-per-Tenant | NeonDB makes shared schema + RLS affordable. Database-per-tenant is complex: requires dynamic connection management, harder to aggregate data, NeonDB still charges per database. Use database-per-tenant only if full blast isolation is compliance requirement (e.g., healthcare). |
| **Credentials Table Location** | Separate encrypted table | Inline in users table | Separates concerns: credentials are sensitive, users table includes profile data. Easier to audit, rotate, and delete credentials independently. |
| **Key Storage** | Environment variables (local) + secrets manager (prod) | Hardcoded, files on disk, database | Never hardcode. Never store keys in git. Environment variables + AWS Secrets Manager / Azure Key Vault / HashiCorp Vault are standard. For local dev, python-dotenv loads from .env. |

---

## Credential Encryption: Deep Dive

### Why Fernet?

Fernet provides "authenticated encryption" out of the box:

1. **Symmetric AES-128-CBC** for confidentiality
2. **HMAC-SHA256** for authenticity (prevents tampering)
3. **Timestamps** to detect old tokens
4. **Base64 URL-safe encoding** for safe database storage
5. **Key rotation support** via MultiFernet (rotate without data migration)

Example key generation:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Output: 8YklPJ4b3pM7x9_QqZ2w5VmN0aB6cD1eF2gH3jK4lM=
```

### Key Management

**Development:**
```bash
# Generate key once
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > .env

# Load in FastAPI startup
from dotenv import load_dotenv
load_dotenv()
key = os.environ.get("FERNET_KEY")  # Must be bytes for Fernet
```

**Production:**
- Store key in AWS Secrets Manager, Azure Key Vault, or HashiCorp Vault
- FastAPI startup fetches key at initialization
- Rotate key every 90 days using MultiFernet

**Key Rotation Pattern (when key compromised):**
```python
from cryptography.fernet import MultiFernet

# Old key and new key
old_key = b"..."
new_key = Fernet.generate_key()

# Create MultiFernet with new key first (write), old key second (read)
multi = MultiFernet([new_key, old_key])

# Decrypt with old key, re-encrypt with new key
plaintext = multi.decrypt(encrypted_data)
new_encrypted = Fernet(new_key).encrypt(plaintext)
```

### Data Sensitivity

Only encrypt the API credentials:
```python
# DO encrypt
api_key_encrypted: LargeBinary  # Secret
secret_key_encrypted: LargeBinary  # Secret

# DON'T encrypt (unnecessary)
user_id: UUID  # Not secret
account_id: str  # Public Alpaca account ID
created_at: datetime  # Metadata

# Over-encryption causes performance penalties and no added security
```

---

## Multi-Tenant Isolation: RLS + sqlalchemy-tenants

### Why RLS?

Database-level isolation prevents application bugs from leaking data:

1. **Query-level enforcement**: A single buggy query (`SELECT * FROM credentials`) still respects RLS
2. **No runtime overhead for correct queries**: Native SQL filter
3. **Audit trail**: All accesses logged to PostgreSQL (with `log_statement = 'all'`)

### Setup Pattern

```python
# Define Tenant and User models
from sqlalchemy_tenants import TenantMixin

class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str]

class User(TenantMixin, Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    email: Mapped[str]

class UserAlpacaCredential(TenantMixin, Base):
    __tablename__ = "user_alpaca_credentials"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    api_key_encrypted: Mapped[bytes]
    # RLS policy automatically filters by tenant_id
```

### In Requests

```python
# FastAPI middleware sets tenant context
@app.middleware("http")
async def set_tenant_context(request: Request, call_next):
    user = await get_current_user(request)
    set_tenant(user.tenant_id)  # sqlalchemy-tenants handles RLS
    response = await call_next(request)
    return response

# Now all queries in this request auto-filter by tenant
# Even if developer forgets to check tenant_id, RLS blocks it
```

---

## Alpaca Integration: Multi-Account Pattern

### Core Challenge

Alpaca's alpaca-py SDK is **account-agnostic**—it takes credentials and uses them. To support multiple users with different Alpaca accounts:

1. **Don't**: Share one Alpaca account across users (data privacy violation)
2. **Do**: Each user has their own Alpaca credentials in the database, encrypted

### Implementation

```python
from alpaca.broker import BrokerClient
from alpaca.trading import TradingClient

async def get_trading_client_for_user(
    user_id: UUID,
    db: AsyncSession
) -> TradingClient:
    """Fetch user's credentials, decrypt, return client"""
    cred = await db.execute(
        select(UserAlpacaCredential).where(
            UserAlpacaCredential.user_id == user_id
        ).limit(1)  # Get primary account; support multiple later
    )
    credential = cred.scalar_one()

    # Decrypt
    api_key = credential.get_api_key()
    secret_key = credential.get_secret_key()

    # Return initialized client
    return TradingClient(
        api_key=api_key,
        secret_key=secret_key,
        base_url="https://api.alpaca.markets"  # Or paper trading URL
    )

# In endpoint
@app.get("/api/my-accounts")
async def list_user_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch user's stored Alpaca credentials
    creds = await db.execute(
        select(UserAlpacaCredential).where(
            UserAlpacaCredential.user_id == current_user.id
        )
    )
    credentials = creds.scalars().all()

    accounts = []
    for cred in credentials:
        # Each credential is a separate Alpaca account
        client = TradingClient(
            api_key=cred.get_api_key(),
            secret_key=cred.get_secret_key()
        )
        account = await client.get_account()  # API call
        accounts.append({
            "id": cred.id,
            "alpaca_account": account.account_number,
            "buying_power": account.buying_power,
            "is_live": cred.is_live
        })

    return {"accounts": accounts}
```

### Alpaca's OmniSub for Scale

If you later need to manage **hundreds of accounts** under institutional rules, Alpaca offers **OmniSub**:

- Partner holds one master omnibus account with Alpaca Securities
- Sub-accounts are tracked via Alpaca's internal DB, not separate live accounts
- Ideal for fintech platforms, RIAs, hedge funds
- Requires formal partnership agreement + compliance

For the current use case (friends trading), individual Alpaca accounts + encrypted storage is the right approach.

---

## Key Rotation & Credential Lifecycle

### Initial Setup
```python
# User adds their Alpaca API keys via UI form
# FastAPI validates format, encrypts, stores

@app.post("/api/credentials/add-alpaca")
async def add_alpaca_credential(
    request: AddCredentialRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Validate key format (basic regex or Alpaca validation call)
    if not is_valid_alpaca_key(request.api_key):
        raise HTTPException(status_code=400, detail="Invalid API key format")

    # Create encrypted credential
    cred = UserAlpacaCredential(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        account_id=request.account_id or "primary"
    )
    cred.set_api_key(request.api_key)
    cred.set_secret_key(request.secret_key)

    db.add(cred)
    await db.commit()

    return {"status": "stored"}
```

### Rotation (90-day cycle or on compromise)
```python
# Admin endpoint to rotate encryption key
# Requires re-encrypting all credentials with new key

async def rotate_encryption_key(new_key: bytes, db: AsyncSession):
    """
    Called monthly or on-demand via admin panel.
    Decrypt with old key, re-encrypt with new.
    """
    # Get all credentials
    all_creds = await db.execute(
        select(UserAlpacaCredential)
    )
    credentials = all_creds.scalars().all()

    # Decrypt with old key, re-encrypt with new
    for cred in credentials:
        api_plaintext = cred.get_api_key()  # Uses old key
        secret_plaintext = cred.get_secret_key()

        # Update encryption key in memory
        os.environ["FERNET_KEY"] = new_key.decode()

        cred.set_api_key(api_plaintext)  # Uses new key
        cred.set_secret_key(secret_plaintext)

        db.add(cred)

    await db.commit()
```

---

## Installation & Setup

### Dependencies

```bash
# Core additions for multi-tenancy + encryption
uv pip install cryptography==47.0.0
uv pip install sqlalchemy-tenants==0.1.0
uv pip install python-dotenv==1.0.0

# Already existing
# fastapi, sqlalchemy, alpaca-py, neon-postgres-python
```

### Environment Variables

```bash
# .env (development)
FERNET_KEY=8YklPJ4b3pM7x9_QqZ2w5VmN0aB6cD1eF2gH3jK4lM=
DATABASE_URL=postgresql://user:pass@localhost/alpaca_db
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

```python
# FastAPI startup
from dotenv import load_dotenv
import os

load_dotenv()

FERNET_KEY = os.environ.get("FERNET_KEY")
if not FERNET_KEY:
    raise ValueError("FERNET_KEY not set in environment")

# Validate key format
try:
    Fernet(FERNET_KEY.encode())
except InvalidToken:
    raise ValueError("Invalid FERNET_KEY format")
```

### Database Migration

```python
# alembic/versions/xxx_add_user_alpaca_credentials.py

def upgrade():
    op.create_table(
        'user_alpaca_credentials',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.String(), nullable=True),
        sa.Column('api_key_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('secret_key_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('is_live', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'account_id')
    )

    # Enable RLS
    op.execute("ALTER TABLE user_alpaca_credentials ENABLE ROW LEVEL SECURITY")

    # Create RLS policy
    op.execute("""
        CREATE POLICY user_credentials_isolation
        ON user_alpaca_credentials
        USING (user_id = current_user_id())
    """)

def downgrade():
    op.drop_table('user_alpaca_credentials')
```

---

## Security Checklist

- [x] **Encryption at rest**: Fernet with Fernet.generate_key()
- [x] **Key isolation**: Stored in environment / secrets manager, never in code
- [x] **Multi-tenant isolation**: PostgreSQL RLS + sqlalchemy-tenants
- [x] **Access control**: User can only see own credentials via RLS
- [x] **Audit logging**: Enable PostgreSQL statement logging for compliance
- [x] **Key rotation**: MultiFernet pattern for zero-downtime rotation
- [x] **Least privilege**: Credentials table only contains what's needed
- [x] **Transport**: HTTPS only (FastAPI default with uvicorn behind reverse proxy)
- [x] **Memory safety**: Decrypted keys in memory only during API call, not cached

---

## Known Limitations & Future Scaling

| Scenario | Current Stack | When to Upgrade |
|----------|---------------|-----------------|
| <1,000 users | Sufficient | N/A |
| 1,000-10,000 users | Start monitoring key rotation overhead | Consider AWS KMS or Vault |
| >10,000 users | App-level encryption becomes bottleneck | Move to managed secret vault |
| Multi-region / global | Fernet keys in env vars don't replicate | Use AWS Secrets Manager with global replication |
| Compliance (PCI-DSS, HIPAA) | RLS + encryption covers most; audit logs required | Add VPC isolation, WAF, DLP scanning |

---

## Comparison to Alternatives

### Why NOT: Store credentials plaintext in database

- **Risk**: Data breach exposes all user API keys
- **Compliance**: Violates security best practices, fails audits

### Why NOT: Client-side encryption only

- **Risk**: Key stored in frontend, exposed via devtools or XSS
- **Trust**: Server still sees plaintext (TLS only)

### Why NOT: AWS Secrets Manager from day one

- **Overhead**: Network call per credential access (adds latency)
- **Cost**: ~$0.40/secret/month; small for MVP
- **Complexity**: Overkill for <1000 users on single deployment
- **When to adopt**: Multi-region, compliance requirements, or >10k users

### Why NOT: Database-per-tenant architecture

- **Overhead**: NeonDB charges per database; N databases = N costs
- **Complexity**: Dynamic connection pools, harder to migrate
- **PostgreSQL RLS**: Achieves same isolation in one database
- **When to adopt**: Compliance requires hard isolation (healthcare, legal)

---

## Sources

### Encryption
- [Cryptography.io - Fernet Documentation](https://cryptography.io/en/latest/fernet/) - Official reference for Fernet API, security properties
- [Medium - Encryption at Rest with Python](https://parthibanmarimuthu.medium.com/securely-encrypting-sensitive-data-in-python-with-fernet-dd50638bde0f) - MEDIUM confidence
- [GeeksforGeeks - Fernet Symmetric Encryption](https://www.geeksforgeeks.org/python/fernet-symmetric-encryption-using-cryptography-module-in-python/) - MEDIUM confidence

### Multi-Tenancy
- [Python FastAPI Postgres SqlAlchemy Row Level Security Multitenancy](https://adityamattos.com/multi-tenancy-in-python-fastapi-and-sqlalchemy-using-postgres-row-level-security) - MEDIUM confidence, practical examples
- [Designing Your Postgres Database for Multi-tenancy - Crunchy Data Blog](https://www.crunchydata.com/blog/designing-your-postgres-database-for-multi-tenancy) - MEDIUM confidence, authoritative source
- [PostgreSQL CDC Multi-Tenant Setups](https://streamkap.com/resources-and-guides/postgresql-cdc-multi-tenant) - MEDIUM confidence
- [AWS Prescriptive Guidance - Multi-tenant SaaS partitioning models](https://docs.aws.amazon.com/prescriptive-guidance/latest/saas-multitenant-managed-postgresql/partitioning-models.html) - HIGH confidence, AWS authority

### SQLAlchemy + Encryption
- [Atlas - Using Row-Level Security In SQLAlchemy](https://atlasgo.io/guides/orms/sqlalchemy/row-level-security) - MEDIUM confidence
- [GitHub - sqlalchemy-tenants](https://github.com/Telemaco019/sqlalchemy-tenants) - HIGH confidence, library source
- [PyPI - encrypt-decrypt-fields](https://pypi.org/project/encrypt-decrypt-fields/) - HIGH confidence, library documentation

### Alpaca API
- [GitHub - alpaca-py Official SDK](https://github.com/alpacahq/alpaca-py) - HIGH confidence, official source
- [Alpaca Docs - Getting Started](https://alpaca.markets/sdks/python/getting_started.html) - HIGH confidence, official documentation
- [Alpaca Blog - OmniSub for Broker API](https://alpaca.markets/blog/introducing-omnisub-for-broker-api-alpacas-powerful-technology-for-sub-accounting/) - HIGH confidence, official announcement

### SaaS Best Practices
- [Frontegg - How to Secure User Credentials on Multi Tenant SaaS](https://frontegg.com/blog/how-to-secure-user-credentials-on-multi-tenant-saas-applications) - MEDIUM confidence
- [AWS - Multi-tenant SaaS authorization and API access control](https://docs.aws.amazon.com/prescriptive-guidance/latest/saas-multitenant-api-access-authorization/introduction.html) - HIGH confidence, AWS authority
- [Medium - Architecting Secure Multi-Tenant Data Isolation](https://medium.com/@justhamade/architecting-secure-multi-tenant-data-isolation-d8f36cb0d25e) - MEDIUM confidence

### NeonDB
- [Neon Docs - Multitenancy](https://neon.com/docs/guides/multitenancy) - HIGH confidence, official documentation
- [Neon Blog - Multi-tenancy and Database-per-User Design](https://neon.com/blog/multi-tenancy-and-database-per-user-design-in-postgres) - MEDIUM confidence, official blog

---

## Recommendations Summary

**For this milestone (adding multi-user support):**

1. **Use Fernet from `cryptography` library** (v47.0.0+) for credential encryption. It's battle-tested, provides authenticated encryption out of the box, and eliminates common cryptographic mistakes.

2. **Implement PostgreSQL Row-Level Security** with `sqlalchemy-tenants` library. Let the database enforce isolation—don't rely on application-level filtering.

3. **Create a dedicated `user_alpaca_credentials` table** with encrypted api_key and secret_key columns. Decrypt only when making API calls; never cache decrypted keys.

4. **Store the Fernet key in environment variables** (local dev via `.env`, production via AWS Secrets Manager or equivalent). Rotate every 90 days or on compromise using MultiFernet pattern.

5. **Keep Alpaca integration simple**: Use `alpaca-py` SDK as-is. Each user's credential → one alpaca-py client instance → one account. No need for OmniSub or sub-accounting until you scale to institutional volume.

This approach is **secure, simple, and sufficient** for the current use case. It trades minimal complexity for strong security guarantees at the database level.
