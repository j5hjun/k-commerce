import json
from pathlib import Path


class CoupangSessionStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.storage_state_path = base_dir / "storage-state.json"
        self.session_meta_path = base_dir / "session-meta.json"

    def ensure_dir(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def has_storage_state(self) -> bool:
        return self.storage_state_path.is_file()

    def write_metadata(self, payload: dict[str, str]) -> None:
        self.ensure_dir()
        self.session_meta_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
