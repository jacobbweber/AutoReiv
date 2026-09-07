"""
Remote Host Domain Models [CARD-160].
"""

from typing import Optional

from pydantic import BaseModel, Field


class RemoteHost(BaseModel):
    id: str = Field(description="Unique remote host identifier")
    label: str = Field(description="Human readable label for the host")
    host: str = Field(description="Hostname or IP address")
    port: int = Field(default=22, description="SSH port (default 22)")
    username: str = Field(description="SSH login username")
    auth_type: str = Field(default="password", description="Authentication type: 'password' or 'key'")
    credential_id: Optional[str] = Field(default=None, description="Vault Credential ID providing secret")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
