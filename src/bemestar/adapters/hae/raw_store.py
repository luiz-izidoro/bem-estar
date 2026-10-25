from __future__ import annotations

import gzip
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path


class RawStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, payload: bytes, payload_hash: str, stream: str) -> Path:
        now = datetime.now(UTC)
        directory = self.root / f"{now:%Y}" / f"{now:%m}" / f"{now:%d}"
        directory.mkdir(parents=True, exist_ok=True)
        final = directory / f"{now:%H%M%S}_{stream}_{payload_hash[:16]}.json.gz"
        temp = final.with_name(final.name + f".{uuid.uuid4().hex}.tmp")
        with gzip.open(temp, "wb", compresslevel=6) as handle:
            handle.write(payload)
        os.replace(temp, final)
        return final

    def read(self, path: str) -> bytes:
        with gzip.open(path, "rb") as handle:
            return handle.read()
