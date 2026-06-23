import tempfile
import unittest
from pathlib import Path
import json

from k_commerce_cli.providers.coupang.session_store import CoupangSessionStore


class CoupangSessionStoreTests(unittest.TestCase):
    def test_storage_state_path_uses_provider_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CoupangSessionStore(base_dir=Path(tmpdir))

            self.assertEqual(store.storage_state_path, Path(tmpdir) / "storage-state.json")

    def test_has_storage_state_is_false_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CoupangSessionStore(base_dir=Path(tmpdir))

            self.assertFalse(store.has_storage_state())

    def test_write_metadata_creates_session_meta_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CoupangSessionStore(base_dir=Path(tmpdir))

            store.write_metadata({"login_method": "automatic"})

            self.assertTrue(store.session_meta_path.exists())
            self.assertEqual(
                json.loads(store.session_meta_path.read_text(encoding="utf-8")),
                {"login_method": "automatic"},
            )
