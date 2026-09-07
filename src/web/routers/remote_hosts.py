"""
Remote Hosts REST API Router [CARD-160].
"""

import re
import time
from typing import Any, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.domain.remote.models import RemoteHost

router = APIRouter(prefix="/api/remote_hosts", tags=["Remote Hosts"])


class RemoteHostPayload(BaseModel):
    id: Optional[str] = None
    label: str = Field(description="Human readable label for the host")
    host: str = Field(description="Hostname or IP address")
    port: Optional[int] = Field(default=22, description="SSH port (default 22)")
    username: str = Field(description="SSH login username")
    auth_type: Optional[str] = Field(default="password", description="'password' or 'key'")
    credential_id: Optional[str] = Field(default=None, description="Vault credential ID")


def _get_store(request: Request):
    store = getattr(request.app.state, "store", None)
    if not store:
        raise HTTPException(status_code=500, detail="Database store not configured")
    return store


def _probe_ssh(host: RemoteHost, store: Any) -> Tuple[bool, float, str]:
    """Attempts an SSH handshake probe using Paramiko in memory."""
    import io

    import paramiko

    secret = ""
    if host.credential_id:
        try:
            cred = store.get_credential(host.credential_id)
            if cred and cred.secret:
                secret = cred.secret
        except Exception:
            pass

    start = time.time()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if host.auth_type == "key" or (secret and "-----BEGIN" in secret):
            pkey = None
            key_f = io.StringIO(secret)
            # Try RSA, then Ed25519, then ECDSA
            for key_cls in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
                try:
                    key_f.seek(0)
                    pkey = key_cls.from_private_key(key_f)
                    break
                except Exception:
                    continue
            client.connect(
                hostname=host.host,
                port=host.port or 22,
                username=host.username,
                pkey=pkey,
                timeout=5,
                look_for_keys=False,
                allow_agent=False,
            )
        else:
            client.connect(
                hostname=host.host,
                port=host.port or 22,
                username=host.username,
                password=secret or None,
                timeout=5,
                look_for_keys=False,
                allow_agent=False,
            )
        client.close()
        latency = round((time.time() - start) * 1000, 2)
        return True, latency, "Connected successfully"
    except Exception as exc:
        latency = round((time.time() - start) * 1000, 2)
        return False, latency, str(exc)


@router.get("", response_model=List[RemoteHost])
async def list_remote_hosts(request: Request):
    """List all configured remote host profiles."""
    store = _get_store(request)
    return store.list_remote_hosts()


@router.post("")
async def create_or_update_remote_host(request: Request, body: RemoteHostPayload):
    """Create or update a remote host profile."""
    store = _get_store(request)

    host_id = body.id
    if not host_id or not host_id.strip():
        slug = re.sub(r"[^a-z0-9]+", "-", body.label.lower()).strip("-")
        host_id = slug or f"host-{int(time.time())}"
    else:
        host_id = re.sub(r"[^a-z0-9_-]+", "-", host_id.lower()).strip("-")

    host = RemoteHost(
        id=host_id,
        label=body.label.strip(),
        host=body.host.strip(),
        port=body.port or 22,
        username=body.username.strip(),
        auth_type=body.auth_type or "password",
        credential_id=body.credential_id.strip() if body.credential_id else None,
    )

    success = store.save_remote_host(host)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save remote host")

    return {"status": "created", "id": host.id, "host": host}


@router.delete("/{host_id}")
async def delete_remote_host(request: Request, host_id: str):
    """Delete a remote host profile."""
    store = _get_store(request)
    deleted = store.delete_remote_host(host_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Host not found")
    return {"status": "deleted", "id": host_id}


@router.post("/{host_id}/test")
async def test_remote_host(request: Request, host_id: str):
    """Run an SSH connectivity probe against the specified host."""
    store = _get_store(request)
    host = store.get_remote_host(host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    ok, latency_ms, msg = _probe_ssh(host, store)
    return {
        "status": "ok" if ok else "error",
        "latency_ms": latency_ms,
        "message": msg,
    }
