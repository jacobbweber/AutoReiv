"""
Unit tests for Credential Vault AES-256-GCM encryption and repository [CARD-168].
"""

from src.domain.security.vault import Credential, CredentialVault
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def test_credential_vault_encryption_roundtrip(tmp_path):
    key_file = tmp_path / ".vault_key"
    vault = CredentialVault(key_file=key_file)

    secret = "ghp_super_secret_token_12345"
    encrypted, nonce = vault.encrypt(secret)

    assert encrypted != secret
    assert isinstance(encrypted, str)
    assert isinstance(nonce, str)

    decrypted = vault.decrypt(encrypted, nonce)
    assert decrypted == secret


def test_credential_repository_crud(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    store.initialize_db()

    cred = Credential(
        id="gh-token",
        name="GitHub Personal Access Token",
        type="token",
        description="For repository operations",
        secret="ghp_live_test_secret_abc123",
    )

    saved = store.save_credential(cred)
    assert saved is True

    # Get single credential with plaintext secret (for authorized execution)
    retrieved = store.get_credential("gh-token")
    assert retrieved is not None
    assert retrieved.id == "gh-token"
    assert retrieved.name == "GitHub Personal Access Token"
    assert retrieved.secret == "ghp_live_test_secret_abc123"

    # List credentials - must NOT expose plaintext secret by default
    listed = store.list_credentials()
    assert len(listed) >= 1
    item = next(c for c in listed if c["id"] == "gh-token")
    assert item["name"] == "GitHub Personal Access Token"
    assert "secret" not in item or item["secret"] == ""

    # Verify secret is encrypted in database directly
    conn = store._get_connection()
    cur = conn.cursor()
    cur.execute("SELECT encrypted_value FROM credentials WHERE id = 'gh-token'")
    row = cur.fetchone()
    assert row is not None
    assert "ghp_live_test_secret_abc123" not in row[0]
    conn.close()

    # Delete credential
    deleted = store.delete_credential("gh-token")
    assert deleted is True
    assert store.get_credential("gh-token") is None
