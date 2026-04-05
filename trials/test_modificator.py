import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import json

from source.constants import Change, Transfer, MOD_DEF_FILE_NAME
from source.messaging import InternalError
import source.modificator as modificator


class Test_Modificator(unittest.TestCase):

    def setUp(self):
        # Patch the global state used throughout modificator
        self.patcher_state = patch('source.modificator.core.state')
        self.mock_state = self.patcher_state.start()
        self.mock_state.library = "C:/Fake/Library"
        self.mock_state.exceptions = ["obsolete"]
        self.mock_state.install_path = "C:/Fake/Install"
        self.mock_state.games = ["BFME2", "RotWK"]

    def tearDown(self):
        self.patcher_state.stop()

    # --- 1. Testing Utility and Hashing Functions ---

    @patch('os.listdir', return_value=["ModA", "obsolete", "ModB"])
    @patch('os.path.isfile')
    def test_mods_detect_new(self, mock_isfile, mock_listdir):
        """ Tests that it flags folders missing a mod definition, ignoring exceptions. """

        # ModA is missing the file, ModB has it
        def fake_isfile(path):
            if "ModA" in path: return False
            return True

        mock_isfile.side_effect = fake_isfile

        result = modificator.mods_detect_new()

        # It should ignore 'obsolete', find ModA is missing it, and skip ModB
        self.assertIn("ModA", result)
        self.assertNotIn("ModB", result)
        self.assertNotIn("obsolete", result)

    @patch('xxhash.xxh128')
    def test_hash_file(self, mock_xxhash):
        """ Tests that file hashing correctly reads bytes and generates a digest. """
        mock_digest = MagicMock()
        mock_digest.hexdigest.return_value = "fake_hash_123"
        mock_xxhash.return_value = mock_digest

        with patch('builtins.open', mock_open(read_data=b"dummy content")):
            result = modificator.hash_file("dummy.ini")

        self.assertEqual(result, "fake_hash_123")
        mock_xxhash.assert_called_once_with(b"dummy content")

    # --- 2. Testing Snapshot Generation and Comparison ---

    @patch('source.modificator.hash_directory')
    def test_snapshot_take(self, mock_hash_dir):
        """ Tests snapshot routing and relative path omission logic. """
        mock_hash_dir.return_value = {"data/file.ini": "hash1"}

        # Test taking a snapshot of a library mod
        result = modificator.snapshot_take(["C:/Fake/Library/TestMod"])

        self.assertIn("date", result)
        self.assertEqual(result["data/file.ini"], "hash1")
        # Ensure path_to_omit stripped the library correctly
        mock_hash_dir.assert_called_with("C:/Fake/Library/TestMod", path_to_omit="C:/Fake/Library/TestMod")

    def test_snapshot_compare_dict(self):
        """ Tests the core logical comparison engine. """
        snap_anterior = {
            "date": "2026-01-01",
            "file_unchanged.ini": "hashA",
            "file_changed.ini": "hashB",
            "file_removed.ini": "hashC"
        }
        snap_posterior = {
            "date": "2026-01-02",
            "file_unchanged.ini": "hashA",
            "file_changed.ini": "hashX",  # Hash changed!
            "file_added.ini": "hashD"  # New file!
        }

        result = modificator.snapshot_compare(snap_anterior, snap_posterior, return_type='dict')

        self.assertEqual(result["file_unchanged.ini"][0], Change.UNCHANGED)

        self.assertEqual(result["file_changed.ini"][0], Change.CHANGED)
        self.assertEqual(result["file_changed.ini"][1], "hashB")  # Old hash
        self.assertEqual(result["file_changed.ini"][2], "hashX")  # New hash

        self.assertEqual(result["file_removed.ini"][0], Change.REMOVED)
        self.assertEqual(result["file_added.ini"][0], Change.ADDED)

    # --- 3. Testing the Comparison Mappers ---

    @patch('source.modificator.hash_directory')
    @patch('source.modificator.snapshot_take')
    @patch('source.modificator.snapshot_save')
    def test_map_changes_from_direct_path(self, mock_save, mock_take, mock_hash):
        """ Tests generating ADDED changes from a raw directory. """
        mock_hash.return_value = {"file1.ini": "hash1", "file2.ini": "hash2"}

        active, changes = modificator.map_changes_from_direct_path("C:/Fake/Mod")

        self.assertTrue(active)
        self.assertEqual(len(changes), 2)
        self.assertEqual(changes["file1.ini"], [Change.ADDED, "hash1"])

    @patch('source.modificator.map_changes_from_direct_path')
    @patch('source.modificator.map_changes_from_directory')
    @patch('os.path.isdir', return_value=True)
    def test_initiate_comparison_router(self, mock_isdir, mock_map_dir, mock_map_direct):
        """ Tests that the orchestrator routes to the correct helper function. """
        mock_map_direct.return_value = (True, {"file": "data"})

        # Test routing to direct path
        active, changes = modificator.initiate_comparison("C:/Fake/Mod", changes_source="C:/Fake/Source")
        mock_map_direct.assert_called_once_with("C:/Fake/Source")
        self.assertTrue(active)

    # --- 4. Testing the Transfer Engine ---

    @patch('os.makedirs')
    @patch('source.modificator.copy2')
    def test_make_transfer_copy(self, mock_copy2, mock_makedirs):
        modificator.make_transfer("src.ini", "C:/dest", Transfer.COPY)
        mock_makedirs.assert_called_once_with("C:/dest", exist_ok=True)
        mock_copy2.assert_called_once_with("src.ini", "C:/dest")

    @patch('os.makedirs')
    @patch('source.modificator.move')
    def test_make_transfer_move(self, mock_move, mock_makedirs):
        modificator.make_transfer("src.ini", "C:/dest", Transfer.MOVE)
        mock_move.assert_called_once_with("src.ini", "C:/dest")

    @patch('os.remove')
    def test_make_transfer_delete(self, mock_remove):
        modificator.make_transfer("src.ini", "C:/dest", Transfer.DELETE)
        mock_remove.assert_called_once_with("src.ini")

    @patch('os.path.isfile', return_value=True)
    @patch('source.modificator.copy2')
    @patch('os.makedirs')
    def test_make_transfer_fallback_logic(self, mock_makedirs, mock_copy2, mock_isfile):
        """ Tests the brilliant OSError fallback logic for .bak and .disabled files. """

        # We simulate an OSError the FIRST time copy2 is called (e.g. file is locked/missing)
        # But the SECOND time it is called (with the .bak file), it succeeds.
        mock_copy2.side_effect = [OSError("File in use"), None]

        # Call make_transfer for a .big file. It will fail, catch the OSError, 
        # see that a .bak file exists (mock_isfile=True), and try again.
        modificator.make_transfer("data.big", "C:/dest", Transfer.COPY, error_sensitive=True)

        self.assertEqual(mock_copy2.call_count, 2)
        # First attempt:
        mock_copy2.assert_any_call("data.big", "C:/dest")
        # Fallback attempt triggered recursively:
        mock_copy2.assert_any_call("data.big.bak", "C:/dest")


if __name__ == '__main__':
    unittest.main()
