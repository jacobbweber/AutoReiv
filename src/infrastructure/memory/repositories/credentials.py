"""
Credential Vault SQLite Repository Mixin [CARD-168].
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.domain.security.vault import Credential, CredentialVault


class CredentialRepositoryMixin:
    """Methods for persisting AES-256-GCM encrypted credentials."""

    def _get_vault(self) -> CredentialVault:
        if not hasattr(self, "_vault") or self._vault is None:
            key_file = None
            if hasattr(self, "db_path") and self.db_path and self.db_path != ":memory:":
                key_file = Path(self.db_path).parent / ".vault_key"
            self._vault = CredentialVault(key_file=key_file)
        return self._vault

    def _init_credentials_table(self, conn) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS credentials (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                encrypted_value TEXT NOT NULL,
                nonce TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

    def save_credential(self, cred: Credential) -> bool:
        """Encrypt and save a credential to SQLite."""
        now_str = datetime.now(timezone.utc).isoformat()
        vault = self._get_vault()
        encrypted_val, nonce = vault.encrypt(cred.secret or "")
        created_at = cred.created_at or now_str

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO credentials (id, name, type, encrypted_value, nonce, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    type = excluded.type,
                    encrypted_value = excluded.encrypted_value,
                    nonce = excluded.nonce,
                    description = excluded.description,
                    updated_at = excluded.updated_at
                """,
                (
                    cred.id,
                    cred.name,
                    cred.type,
                    encrypted_val,
                    nonce,
                    cred.description or "",
                    created_at,
                    now_str,
                ),
            )
            conn.commit()
            return True
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_credential(self, cred_id: str) -> Optional[Credential]:
        """Retrieve and decrypt a credential by ID."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, type, encrypted_value, nonce, description, created_at, updated_at
                FROM credentials WHERE id = ?
                """,
                (cred_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            vault = self._get_vault()
            decrypted = vault.decrypt(row["encrypted_value"], row["nonce"])
            return Credential(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                description=row["description"] or "",
                secret=decrypted,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_credentials(self, include_secret: bool = False) -> List[Dict[str, Any]]:
        """List all credentials metadata, with masked preview and strictly no plaintext by default."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, type, encrypted_value, nonce, description, created_at, updated_at
                FROM credentials ORDER BY name ASC
                """
            )
            rows = cur.fetchall()
            result = []
            vault = self._get_vault()
            for r in rows:
                item = {
                    "id": r["id"],
                    "name": r["name"],
                    "type": r["type"],
                    "description": r["description"] or "",
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                }
                if include_secret:
                    item["secret"] = vault.decrypt(r["encrypted_value"], r["nonce"])
                    item["masked_preview"] = self._mask_secret(item["secret"])
                else:
                    try:
                        decrypted = vault.decrypt(r["encrypted_value"], r["nonce"])
                        item["masked_preview"] = self._mask_secret(decrypted)
                    except Exception:
                        item["masked_preview"] = "••••••••"
                result.append(item)
            return result
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_credential(self, cred_id: str) -> bool:
        """Delete credential from SQLite storage."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM credentials WHERE id = ?", (cred_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()

    @staticmethod
    def _mask_secret(secret: str) -> str:
        s = str(secret or "")
        if len(s) <= 4:
            return "****"
        return f"****...{s[-4:]}"
