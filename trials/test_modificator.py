import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import json

import source.core as core
import source.modificator as modificator
from source.constants import Transfer, Change


class Test_Modificator(unittest.TestCase):

    def setUp(self):
        # Globally mock the log function to prevent log file spam during testing
        self.patcher_log = patch('source.modificator.log')
        self.mock_log = self.patcher_log.start()
        core.state.library = f"{core.state.install_path}/Fake/Library"

        # We need to ensure os.path.abspath returns our fake paths cleanly
        # because snapshot_take uses it to calculate string slices.
        self.patcher_abspath = patch('os.path.abspath', side_effect=lambda p: p)
        self.patcher_abspath.start()

    def tearDown(self):
        self.patcher_log.stop()
        self.patcher_abspath.stop()

    @patch('source.modificator.hash_file')
    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('source.core.state.games', ['game'])  # Define 'game' as our recognized game folder
    def test_hash_directory(self, mock_isfile, mock_isdir, mock_listdir, mock_hash_file):

        # 1. Setup fake directory structure exactly as requested
        def isdir_mock(path):
            return path in ["Mod", "Mod/game"]

        def isfile_mock(path):
            return path in ["Mod/_definition.json", "Mod/game/file1.txt", "Mod/game/file2.txt"]

        def listdir_mock(path):
            if path == "Mod":
                return ["_definition.json", "game"]
            if path == "Mod/game":
                return ["file1.txt", "file2.txt"]
            return []

        mock_isdir.side_effect = isdir_mock
        mock_isfile.side_effect = isfile_mock
        mock_listdir.side_effect = listdir_mock

        # 2. Pretend hash_file always returns a dummy hash based on the file name
        mock_hash_file.side_effect = lambda filepath: f"hash_of_{filepath.split('/')[-1]}"

        # 3. Call the function
        result = modificator.hash_directory("Mod", path_to_omit="Mod")

        # 4. Assertions
        # _definition.json MUST NOT be in the result because "game" triggered the override logic
        self.assertNotIn("_definition.json", result)

        # The files inside "game" should be properly hashed and correctly sliced relative to "Mod"
        self.assertIn("game/file1.txt", result)
        self.assertEqual(result["game/file1.txt"], "hash_of_file1.txt")
        self.assertIn("game/file2.txt", result)
        self.assertEqual(result["game/file2.txt"], "hash_of_file2.txt")

        # Ensure ONLY the 2 game files were actually hashed
        self.assertEqual(len(result), 2)

    def test_snapshot_compare__dict_mode(self):
        # We pass raw dictionaries to bypass the file loading logic
        snap_anterior = {
            "date": "2023-01-01",
            "file_unchanged.ini": "hash_A",
            "file_changed.ini": "hash_B",
            "file_removed.ini": "hash_C"
        }
        snap_posterior = {
            "date": "2023-01-02",
            "file_unchanged.ini": "hash_A",
            "file_changed.ini": "hash_MODIFIED",
            "file_added.ini": "hash_D"
        }

        result = modificator.snapshot_compare(snap_anterior, snap_posterior, return_type='dict')

        # Verify it categorized the changes correctly according to your enums
        self.assertEqual(result["file_unchanged.ini"][0], Change.UNCHANGED)

        self.assertEqual(result["file_changed.ini"][0], Change.CHANGED)
        self.assertEqual(result["file_changed.ini"][1], "hash_B")  # old hash
        self.assertEqual(result["file_changed.ini"][2], "hash_MODIFIED")  # new hash

        self.assertEqual(result["file_removed.ini"][0], Change.REMOVED)
        self.assertEqual(result["file_added.ini"][0], Change.ADDED)

    @patch('source.modificator.os.remove')
    @patch('source.modificator.move')
    @patch('source.modificator.copy2')
    def test_make_transfer__routing(self, mock_copy, mock_move, mock_remove):
        src = "C:/source/file.txt"
        dst = "C:/dest/file.txt"

        # Test COPY
        modificator.make_transfer(src, dst, transfer_type=Transfer.COPY, error_sensitive=False)
        mock_copy.assert_called_once_with(src, dst)

        # Test MOVE
        modificator.make_transfer(src, dst, transfer_type=Transfer.MOVE, error_sensitive=False)
        mock_move.assert_called_once_with(src, dst)

        # Test DELETE
        modificator.make_transfer(src, dst, transfer_type=Transfer.DELETE, error_sensitive=False)
        mock_remove.assert_called_once_with(src)

    @patch('source.modificator.xxhash')
    @patch('builtins.open', new_callable=mock_open, read_data=b"binary_data")
    def test_hash_file(self, mock_file, mock_xxhash):
        # Set up a mock return for the xxhash algorithm
        mock_xxhash_instance = MagicMock()
        mock_xxhash_instance.hexdigest.return_value = "fake_hash_123"
        mock_xxhash.xxh128.return_value = mock_xxhash_instance

        result = modificator.hash_file("dummy.txt")

        # Verify it opened the file in 'rb' (read-binary) mode
        mock_file.assert_called_once_with("dummy.txt", 'rb')
        mock_xxhash.xxh128.assert_called_once_with(b"binary_data")
        self.assertEqual(result, "fake_hash_123")

    @patch('os.mkdir')
    @patch('os.path.isdir')
    def test_get_available_name__creates_directory(self, mock_isdir, mock_mkdir):
        # Pretend the snapshot directory doesn't exist yet
        mock_isdir.return_value = False

        result = modificator.get_available_name("C:/Snapshots", "file_snapshot_")

        # It should make the directory and start at counter "1"
        mock_mkdir.assert_called_once_with("C:/Snapshots")
        self.assertEqual(result, "C:/Snapshots/file_snapshot_1.json")

    @patch('source.modificator.askstring')
    @patch('os.path.getctime')
    @patch('source.modificator.glob')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_get_available_name__increments_existing(self, mock_isdir, mock_exists, mock_glob, mock_getctime,
                                                     mock_askstring):
        mock_isdir.return_value = True
        mock_exists.return_value = True

        # Pretend there are already 3 snapshots in the folder
        mock_glob.return_value = [
            "C:/Snapshots/file_snapshot_1.json",
            "C:/Snapshots/file_snapshot_2.json",
            "C:/Snapshots/file_snapshot_3.json"
        ]

        # We trick `max(..., key=os.path.getctime)` into picking the file with "3"
        # by extracting the numeric suffix from the string and using it as the "time"
        # (e.g., "1" -> 1, "2" -> 2, "3" -> 3)
        mock_getctime.side_effect = lambda path: int(path.split('_')[-1].split('.')[0])

        result = modificator.get_available_name("C:/Snapshots", "file_snapshot_")

        # It should extract the "3", increment it to "4"
        self.assertEqual(result, "C:/Snapshots/file_snapshot_4.json")
        mock_askstring.assert_not_called()

    @patch('source.modificator.datetime')
    @patch('source.modificator.hash_directory')
    def test_snapshot_take__provided_paths(self, mock_hash_directory, mock_datetime):
        # Freeze time for a predictable dict output
        mock_datetime.now.return_value = "2023-01-01 12:00:00"

        # Provide a fake hash output
        mock_hash_directory.return_value = {"data/ini/file.txt": "fake_hash"}

        # Test taking a snapshot of a specific game path (bypassing UI prompts)
        result = modificator.snapshot_take(game_paths=["O:/Fake/Game/data"])

        # Verify it passed the install_path to be omitted
        mock_hash_directory.assert_called_once_with("O:/Fake/Game/data", path_to_omit=core.state.install_path)

        # Verify the returned dictionary shape
        self.assertEqual(result["date"], "2023-01-01 12:00:00")
        self.assertEqual(result["data/ini/file.txt"], "fake_hash")

    @patch('source.modificator.askdirectory')
    @patch('source.modificator.hash_directory')
    def test_snapshot_take__ui_prompt(self, mock_hash_directory, mock_askdirectory):
        mock_hash_directory.return_value = {}

        # The askdirectory prompt is in a while loop. We return a valid path first,
        # then return an empty string "" to simulate the user clicking "Cancel", which breaks the loop.
        mock_askdirectory.side_effect = ["O:/Fake/Install/MyGame", ""]

        modificator.snapshot_take()

        # Verify it asked for a directory and successfully processed the chosen path
        mock_askdirectory.assert_called()
        mock_hash_directory.assert_called_once_with("O:/Fake/Install/MyGame", path_to_omit=core.state.install_path)

    @patch('source.modificator.get_available_name')
    @patch('json.dump')
    @patch('builtins.open', new_callable=mock_open)
    def test_snapshot_save__no_name(self, mock_file, mock_json_dump, mock_get_name):
        mock_get_name.return_value = "C:/Snapshots/file_snapshot_1.json"

        fake_snapshot = {"date": "today", "file.txt": "hash1"}

        result = modificator.snapshot_save(fake_snapshot)

        # Verify it fetched an auto-incremented name and wrote the JSON to disk
        mock_get_name.assert_called_once_with(modificator.SNAPSHOT_DIRECTORY)
        mock_file.assert_called_once_with("C:/Snapshots/file_snapshot_1.json", 'w')
        mock_json_dump.assert_called_once_with(fake_snapshot, mock_file(), indent=4)
        self.assertEqual(result, "C:/Snapshots/file_snapshot_1.json")

    @patch('source.modificator.snapshot_take')
    @patch('source.modificator.snapshot_save')
    @patch('source.modificator.hash_file')
    @patch('source.modificator.hash_directory')
    @patch('source.modificator.askopenfilenames')
    @patch('source.modificator.askdirectory')
    @patch('os.path.isdir')
    def test_initiate_comparison__directory_mode(
            self, mock_isdir, mock_askdirectory, mock_askopenfilenames,
            mock_hash_directory, mock_hash_file, mock_snapshot_save, mock_snapshot_take
    ):
        # We explicitly tell isdir to return False if the literal keyword "directory"
        # is checked, but True for our actual fake paths.
        mock_isdir.side_effect = lambda path: path != "directory"

        # Pretend the user selects the start mod directory via the UI popup
        mock_askdirectory.return_value = "C:/Fake/StartMod"

        # Pretend the user selects one file they want to remove via the UI popup
        mock_askopenfilenames.return_value = ["C:/Fake/StartMod/data/remove_me.txt"]
        mock_hash_file.return_value = "hash_removed"

        # Mock the directory hashes
        def hash_dir_mock(path, **kwargs):
            if "MyMod" in path:
                return {"data/new_file.txt": "hash_new", "data/changed_file.txt": "hash_changed"}
            elif "StartMod" in path:
                return {"data/changed_file.txt": "hash_old", "data/remove_me.txt": "hash_removed"}
            return {}

        mock_hash_directory.side_effect = hash_dir_mock

        # Run the comparison
        active, changes = modificator.initiate_comparison(
            mod_directory="C:/Fake/Library/MyMod",
            start_mod="",
            changes_source="directory"
        )

        # It should correctly classify the new file, the changed file, and the explicitly removed file
        self.assertFalse(active)
        self.assertEqual(changes["data/new_file.txt"][0], modificator.Change.ADDED)

        self.assertEqual(changes["data/changed_file.txt"][0], modificator.Change.CHANGED)
        self.assertEqual(changes["data/changed_file.txt"][1], "hash_changed")  # new
        self.assertEqual(changes["data/changed_file.txt"][2], "hash_old")  # old

        self.assertEqual(changes["C:/Fake/StartMod/data/remove_me.txt"][0], modificator.Change.REMOVED)
        self.assertEqual(changes["C:/Fake/StartMod/data/remove_me.txt"][1], "hash_removed")


if __name__ == '__main__':
    unittest.main()
