"""
Credential Vault and AES-256-GCM Encryption [CARD-168].
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Union

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTOGRAPHY = True
except ImportError:  # pragma: no cover
    AESGCM = None  # type: ignore
    HAS_CRYPTOGRAPHY = False

from pydantic import BaseModel, Field


class Credential(BaseModel):
    id: str = Field(description="Unique credential ID")
    name: str = Field(description="Human readable name for the credential")
    type: str = Field(default="token", description="Type: token, api_key, ssh_key, connection_string, custom")
    description: str = Field(default="", description="Optional description of usage")
    secret: str = Field(default="", description="Plaintext secret value in memory")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CredentialVault:
    """
    AES-256-GCM Cryptographic Vault for securing sensitive secrets at rest.
    """

    def __init__(self, key_file: Optional[Union[str, Path]] = None, key_bytes: Optional[bytes] = None):
        if not HAS_CRYPTOGRAPHY or AESGCM is None:
            raise RuntimeError(
                "The 'cryptography' library is required to use CredentialVault. "
                "Please install it via: pip install cryptography"
            )
        if key_bytes:
            self._key = key_bytes
        else:
            if key_file:
                path = Path(key_file)
            else:
                base_dir = Path(os.getenv("AUTOREIV_DATA_DIR") or Path.home() / ".autoreiv")
                base_dir.mkdir(parents=True, exist_ok=True)
                path = base_dir / ".vault_key"

            if path.is_file():
                self._key = path.read_bytes()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                self._key = AESGCM.generate_key(bit_length=256)
                try:
                    path.write_bytes(self._key)
                    # Attempt restrictive permissions on Unix
                    os.chmod(path, 0o600)
                except Exception:
                    pass

        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: str) -> Tuple[str, str]:
        """
        Encrypt plaintext string using AES-256-GCM.
        Returns (ciphertext_hex, nonce_hex).
        """
        if plaintext is None:
            plaintext = ""
        nonce = os.urandom(12)  # Standard 96-bit nonce for AES-GCM
        data = plaintext.encode("utf-8")
        ciphertext = self._aesgcm.encrypt(nonce, data, None)
        return ciphertext.hex(), nonce.hex()

    def decrypt(self, ciphertext_hex: str, nonce_hex: str) -> str:
        """
        Decrypt ciphertext_hex using nonce_hex.
        Returns decrypted UTF-8 plaintext string.
        """
        if not ciphertext_hex or not nonce_hex:
            return ""
        try:
            nonce = bytes.fromhex(nonce_hex)
            ciphertext = bytes.fromhex(ciphertext_hex)
            decrypted = self._aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted.decode("utf-8")
        except Exception as exc:
            raise ValueError(f"Decryption failed: {exc}") from exc
