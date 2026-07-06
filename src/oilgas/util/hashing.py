from __future__ import annotations

import hashlib
from pathlib import Path


def sha256(path: Path) -> str:

    digest = hashlib.sha256()

    with path.open("rb") as f:
        while chunk := f.read(65536):
            digest.update(chunk)

    return digest.hexdigest()
