from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticationSettings:
    required: bool
    secret_key: str
    google_client_id: str | None
    google_client_secret: str | None
    allowed_emails: frozenset[str]


def authentication_settings() -> AuthenticationSettings:
    required = os.environ.get("OILGAS_AUTH_REQUIRED", "false").lower() == "true"
    secret_key = os.environ.get("OILGAS_SECRET_KEY", "local-development-only")
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    allowed_emails = frozenset(
        email.strip().casefold()
        for email in os.environ.get("OILGAS_ALLOWED_EMAILS", "").split(",")
        if email.strip()
    )

    if required:
        missing = [
            name
            for name, value in (
                ("OILGAS_SECRET_KEY", os.environ.get("OILGAS_SECRET_KEY")),
                ("GOOGLE_CLIENT_ID", client_id),
                ("GOOGLE_CLIENT_SECRET", client_secret),
                ("OILGAS_ALLOWED_EMAILS", allowed_emails),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Production authentication is enabled but missing: " + ", ".join(missing)
            )

    return AuthenticationSettings(
        required=required,
        secret_key=secret_key,
        google_client_id=client_id,
        google_client_secret=client_secret,
        allowed_emails=allowed_emails,
    )
