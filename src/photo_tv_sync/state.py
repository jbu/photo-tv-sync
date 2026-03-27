import json
from pathlib import Path


class UploadedState:
    """Persists UUIDs of photos that have been successfully uploaded."""

    def __init__(self, path: Path):
        self._path = path
        self._uploaded: set[str] = set()
        if path.exists():
            self._uploaded = set(json.loads(path.read_text()))

    def already_uploaded(self, uuid: str) -> bool:
        return uuid in self._uploaded

    def mark_uploaded(self, uuid: str) -> None:
        self._uploaded.add(uuid)
        self._path.write_text(json.dumps(sorted(self._uploaded), indent=2))

    def reset(self) -> None:
        self._uploaded = set()
        if self._path.exists():
            self._path.unlink()
