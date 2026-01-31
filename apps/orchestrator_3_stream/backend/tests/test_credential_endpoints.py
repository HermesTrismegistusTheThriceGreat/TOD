#!/usr/bin/env python3
"""
Integration tests for credential API endpoints.

Tests all credential CRUD endpoints with proper authentication and RLS enforcement.

Run with: cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_credential_endpoints.py -v
"""

import pytest
import sys
from pathlib import Path
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch
from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from modules.auth_middleware import AuthUser, get_current_user
from routers.credentials import router as credentials_router


# ═══════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def test_encryption_key(monkeypatch):
    """Generate and set test encryption key"""
    test_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("ENCRYPTION_KEY", test_key)
    return test_key


@pytest.fixture
def mock_user():
    """Create mock authenticated user for dependency override"""
    return AuthUser(id="test-user-123", email="test@example.com", name="Test User")


@pytest.fixture
def test_account_id():
    """Test account UUID"""
    return str(uuid4())


@pytest.fixture
def test_credential_id():
    """Test credential UUID"""
    return str(uuid4())


@pytest.fixture
def test_app(mock_user):
    """Create FastAPI app with credential endpoints and mocked auth"""
    app = FastAPI()
    app.include_router(credentials_router)

    # Override get_current_user dependency to return mock user
    app.dependency_overrides[get_current_user] = lambda: mock_user

    return app


@pytest.fixture
def client(test_app):
    """Create test client"""
    return TestClient(test_app)


# ═══════════════════════════════════════════════════════════
# TESTS: POST /api/credentials/store
# ═══════════════════════════════════════════════════════════


@patch("routers.credentials.store_credential")
@patch("routers.credentials.get_connection_with_rls")
def test_store_credential_success(
    mock_get_conn,
    mock_store_cred,
    client,
    test_encryption_key,
    test_account_id,
    test_credential_id,
    mock_user,
):
    """Test successful credential storage"""
    from modules.user_models import UserCredentialORM
    from datetime import datetime

    # Mock database operations
    mock_store_cred.return_value = UUID(test_credential_id)

    # Mock credential object
    mock_cred = UserCredentialORM(
        id=UUID(test_credential_id),
        user_account_id=UUID(test_account_id),
        user_id=mock_user.id,
        credential_type="alpaca_paper",
        api_key="encrypted_api_key",
        secret_key="encrypted_secret_key",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Mock connection and query execution
    mock_conn = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one.return_value = mock_cred
    mock_conn.execute = AsyncMock(return_value=mock_result)
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    # Make request
    response = client.post(
        "/api/credentials/store",
        json={
            "account_id": test_account_id,
            "credential_type": "alpaca_paper",
            "api_key": "PKTEST123456",
            "secret_key": "spABCDEF123456",
        },
    )

    # Assertions
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == test_credential_id
    assert data["account_id"] == test_account_id
    assert data["credential_type"] == "alpaca_paper"
    assert data["is_active"] is True
    assert "api_key" not in data  # Plaintext not in response
    assert "secret_key" not in data  # Plaintext not in response


@patch("routers.credentials.store_credential")
@patch("routers.credentials.get_connection_with_rls")
def test_store_credential_duplicate(
    mock_get_conn, mock_store_cred, client, test_encryption_key, test_account_id
):
    """Test duplicate credential returns 409"""
    from sqlalchemy.exc import IntegrityError

    # Mock IntegrityError for duplicate
    mock_store_cred.side_effect = IntegrityError("", "", "")
    mock_conn = AsyncMock()
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.post(
        "/api/credentials/store",
        json={
            "account_id": test_account_id,
            "credential_type": "alpaca_paper",
            "api_key": "PKTEST123456",
            "secret_key": "spABCDEF123456",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@patch("routers.credentials.store_credential")
@patch("routers.credentials.get_connection_with_rls")
def test_store_credential_unauthorized(
    mock_get_conn, mock_store_cred, client, test_encryption_key, test_account_id
):
    """Test unauthorized account access returns 403"""
    # Mock ValueError for unauthorized access
    mock_store_cred.side_effect = ValueError("Account does not belong to user")
    mock_conn = AsyncMock()
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.post(
        "/api/credentials/store",
        json={
            "account_id": test_account_id,
            "credential_type": "alpaca_paper",
            "api_key": "PKTEST123456",
            "secret_key": "spABCDEF123456",
        },
    )

    assert response.status_code == 403
    assert "does not belong to user" in response.json()["detail"]


def test_store_credential_missing_fields(client, test_encryption_key):
    """Test missing required fields returns 422"""
    response = client.post(
        "/api/credentials/store",
        json={
            "account_id": str(uuid4()),
            # Missing credential_type, api_key, secret_key
        },
    )

    assert response.status_code == 422


# ═══════════════════════════════════════════════════════════
# TESTS: GET /api/credentials
# ═══════════════════════════════════════════════════════════


@patch("routers.credentials.get_connection_with_rls")
def test_list_credentials_success(
    mock_get_conn, client, test_encryption_key, test_account_id, mock_user
):
    """Test successful credential listing"""
    from modules.user_models import UserCredentialORM
    from datetime import datetime

    # Mock credentials
    mock_creds = [
        UserCredentialORM(
            id=uuid4(),
            user_account_id=UUID(test_account_id),
            user_id=mock_user.id,
            credential_type="alpaca_paper",
            api_key="encrypted_key_1",
            secret_key="encrypted_secret_1",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        UserCredentialORM(
            id=uuid4(),
            user_account_id=UUID(test_account_id),
            user_id=mock_user.id,
            credential_type="polygon",
            api_key="encrypted_key_2",
            secret_key="encrypted_secret_2",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]

    # Mock connection and query
    mock_conn = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = mock_creds
    mock_conn.execute = AsyncMock(return_value=mock_result)
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.get(f"/api/credentials?account_id={test_account_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["count"] == 2
    assert len(data["credentials"]) == 2


@patch("routers.credentials.get_connection_with_rls")
def test_list_credentials_no_plaintext(
    mock_get_conn, client, test_encryption_key, test_account_id, mock_user
):
    """Test that response does NOT contain plaintext credentials"""
    from modules.user_models import UserCredentialORM
    from datetime import datetime

    mock_cred = UserCredentialORM(
        id=uuid4(),
        user_account_id=UUID(test_account_id),
        user_id=mock_user.id,
        credential_type="alpaca_paper",
        api_key="encrypted_api_key",
        secret_key="encrypted_secret_key",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    mock_conn = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = [mock_cred]
    mock_conn.execute = AsyncMock(return_value=mock_result)
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.get(f"/api/credentials?account_id={test_account_id}")

    assert response.status_code == 200
    data = response.json()

    # Verify no plaintext in response
    for cred in data["credentials"]:
        assert "api_key" not in cred or cred.get("api_key") is None
        assert "secret_key" not in cred or cred.get("secret_key") is None


# ═══════════════════════════════════════════════════════════
# TESTS: POST /api/credentials/{id}/validate
# ═══════════════════════════════════════════════════════════


@patch("routers.credentials.validate_alpaca_credentials")
@patch("routers.credentials.get_decrypted_alpaca_credential")
@patch("routers.credentials.get_connection_with_rls")
def test_validate_credential_success(
    mock_get_conn,
    mock_get_decrypted,
    mock_validate,
    client,
    test_encryption_key,
    test_credential_id,
):
    """Test successful credential validation"""
    # Mock decrypt context manager
    mock_get_decrypted.return_value.__aenter__.return_value = (
        "PKTEST123456",
        "spABCDEF123456",
    )

    # Mock Alpaca API validation
    mock_validate.return_value = (True, "paper")

    mock_conn = AsyncMock()
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.post(f"/api/credentials/{test_credential_id}/validate")

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["account_type"] == "paper"
    assert "successfully" in data["message"]


@patch("routers.credentials.validate_alpaca_credentials")
@patch("routers.credentials.get_decrypted_alpaca_credential")
@patch("routers.credentials.get_connection_with_rls")
def test_validate_credential_invalid(
    mock_get_conn,
    mock_get_decrypted,
    mock_validate,
    client,
    test_encryption_key,
    test_credential_id,
):
    """Test invalid credential validation"""
    mock_get_decrypted.return_value.__aenter__.return_value = (
        "INVALID_KEY",
        "INVALID_SECRET",
    )
    mock_validate.return_value = (False, None)

    mock_conn = AsyncMock()
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.post(f"/api/credentials/{test_credential_id}/validate")

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert data["account_type"] is None


@patch("routers.credentials.get_decrypted_alpaca_credential")
@patch("routers.credentials.get_connection_with_rls")
def test_validate_credential_inactive(
    mock_get_conn, mock_get_decrypted, client, test_encryption_key, test_credential_id
):
    """Test inactive credential returns 400"""
    # Mock ValueError for inactive credential
    mock_get_decrypted.return_value.__aenter__.side_effect = ValueError(
        "Credential is inactive"
    )

    mock_conn = AsyncMock()
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.post(f"/api/credentials/{test_credential_id}/validate")

    assert response.status_code == 400
    assert "inactive" in response.json()["detail"]


@patch("routers.credentials.get_decrypted_alpaca_credential")
@patch("routers.credentials.get_connection_with_rls")
def test_validate_credential_unauthorized(
    mock_get_conn, mock_get_decrypted, client, test_encryption_key, test_credential_id
):
    """Test unauthorized credential access returns 403"""
    mock_get_decrypted.return_value.__aenter__.side_effect = ValueError(
        "Credential does not belong to user"
    )

    mock_conn = AsyncMock()
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.post(f"/api/credentials/{test_credential_id}/validate")

    assert response.status_code == 403


# ═══════════════════════════════════════════════════════════
# TESTS: PUT /api/credentials/{id}
# ═══════════════════════════════════════════════════════════


@patch("routers.credentials.get_connection_with_rls")
def test_update_credential_success(
    mock_get_conn, client, test_encryption_key, test_credential_id, test_account_id
):
    """Test successful credential update"""
    from modules.user_models import UserCredentialORM
    from datetime import datetime

    mock_cred = UserCredentialORM(
        id=UUID(test_credential_id),
        user_account_id=UUID(test_account_id),
        user_id="test-user-123",
        credential_type="alpaca_paper",
        api_key="new_encrypted_key",
        secret_key="encrypted_secret",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    mock_conn = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = mock_cred
    mock_conn.execute = AsyncMock(return_value=mock_result)
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.put(
        f"/api/credentials/{test_credential_id}",
        json={"api_key": "PKNEW123456"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_credential_id
    assert data["is_active"] is True


@patch("routers.credentials.get_connection_with_rls")
def test_update_credential_deactivate(
    mock_get_conn, client, test_encryption_key, test_credential_id, test_account_id
):
    """Test credential deactivation"""
    from modules.user_models import UserCredentialORM
    from datetime import datetime

    mock_cred = UserCredentialORM(
        id=UUID(test_credential_id),
        user_account_id=UUID(test_account_id),
        user_id="test-user-123",
        credential_type="alpaca_paper",
        api_key="encrypted_key",
        secret_key="encrypted_secret",
        is_active=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    mock_conn = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = mock_cred
    mock_conn.execute = AsyncMock(return_value=mock_result)
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.put(
        f"/api/credentials/{test_credential_id}",
        json={"is_active": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


@patch("routers.credentials.get_connection_with_rls")
def test_update_credential_unauthorized(
    mock_get_conn, client, test_encryption_key, test_credential_id
):
    """Test unauthorized update returns 403"""
    mock_conn = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None  # Credential not found
    mock_conn.execute = AsyncMock(return_value=mock_result)
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.put(
        f"/api/credentials/{test_credential_id}",
        json={"api_key": "PKNEW123456"},
    )

    assert response.status_code == 403


# ═══════════════════════════════════════════════════════════
# TESTS: DELETE /api/credentials/{id}
# ═══════════════════════════════════════════════════════════


@patch("routers.credentials.get_connection_with_rls")
def test_delete_credential_success(
    mock_get_conn, client, test_encryption_key, test_credential_id
):
    """Test successful credential deletion"""
    mock_conn = AsyncMock()
    mock_result = AsyncMock()
    mock_result.rowcount = 1  # One row deleted
    mock_conn.execute = AsyncMock(return_value=mock_result)
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.delete(f"/api/credentials/{test_credential_id}")

    assert response.status_code == 204


@patch("routers.credentials.get_connection_with_rls")
def test_delete_credential_unauthorized(
    mock_get_conn, client, test_encryption_key, test_credential_id
):
    """Test unauthorized deletion returns 403"""
    mock_conn = AsyncMock()
    mock_result = AsyncMock()
    mock_result.rowcount = 0  # No rows deleted (RLS filtered)
    mock_conn.execute = AsyncMock(return_value=mock_result)
    mock_get_conn.return_value.__aenter__.return_value = mock_conn

    response = client.delete(f"/api/credentials/{test_credential_id}")

    assert response.status_code == 403
