import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import json

import source.core as core
import source.shared as s
import source.modificator as modificator
from source.modificator import Property, Transfer, Change, Mod


class Test_Modificator(unittest.TestCase):

    def setUp(self):
        # Globally mock the log function to prevent log file spam during testing
        self.patcher_log = patch('source.modificator.log')
        self.mock_log = self.patcher_log.start()

    def tearDown(self):
        self.patcher_log.stop()

    # --- 1. Test Definitions and Mod Class ---

    def test_mod_initialization(self):
        # A new Mod should auto-populate with the DEFINITION_TEMPLATE keys
        my_mod = Mod()
        self.assertIn(Property.NAME, my_mod)
        self.assertIn(Property.CHANGES, my_mod)
        self.assertEqual(my_mod[Property.ACTIVE], False)

        # It should also accept overrides via initial_dict
        override_mod = Mod(initial_dict={Property.NAME: "TestMod", Property.ACTIVE: True})
        self.assertEqual(override_mod[Property.NAME], "TestMod")
        self.assertTrue(override_mod[Property.ACTIVE])

    @patch('os.path.isfile')
    @patch('builtins.open', new_callable=mock_open, read_data='{"name": "LoadedMod", "active": true}')
    @patch('source.core.exceptions', [])  # Prevent exceptions check from failing
    def test_definition_read(self, mock_file, mock_isfile):
        mock_isfile.return_value = True

        result = modificator.definition_read("C:/Fake/Library/MyMod")

        # Verify it loaded the JSON and converted it into a Mod object
        mock_file.assert_called_once_with("C:/Fake/Library/MyMod/_definition.json")
        self.assertIsInstance(result, Mod)
        self.assertEqual(result[Property.NAME], "LoadedMod")

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_definition_save(self, mock_json_dump, mock_file):
        dummy_mod = Mod({Property.NAME: "SaveMe"})

        modificator.definition_save(dummy_mod, "C:/Fake/Library/SaveMe")

        # Verify it wrote to the correct file path using json.dump
        mock_file.assert_called_once_with("C:/Fake/Library/SaveMe/_definition.json", 'w')
        mock_json_dump.assert_called_once_with(dummy_mod, mock_file(), indent=4)

    # --- 2. Test Hashing and Directory Traversal ---

    @patch('source.modificator.hash_file')
    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('source.core.games', ['game'])  # Define 'game' as our recognized game folder
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

    # --- 3. Test Snapshot Comparison Logic ---

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

    # --- 4. Test File Transfer Router ---

    @patch('source.modificator.os.remove')
    @patch('source.modificator.move')
    @patch('source.modificator.copy2')
    @patch('source.modificator.ensure_path_exists')
    def test_make_transfer__routing(self, mock_ensure_path, mock_copy, mock_move, mock_remove):
        src = "C:/source/file.txt"
        dst = "C:/dest/file.txt"

        # Test COPY
        modificator.make_transfer(src, dst, transfer_type=Transfer.COPY, error_sensitive=False)
        mock_ensure_path.assert_called_with(src, dst)
        mock_copy.assert_called_once_with(src, dst)

        # Test MOVE
        modificator.make_transfer(src, dst, transfer_type=Transfer.MOVE, error_sensitive=False)
        mock_move.assert_called_once_with(src, dst)

        # Test DELETE
        modificator.make_transfer(src, dst, transfer_type=Transfer.DELETE, error_sensitive=False)
        mock_remove.assert_called_once_with(src)


class Test_Modificator_Attach(unittest.TestCase):

    def setUp(self):
        # Prevent actual logging
        self.patcher_log = patch('source.modificator.log')
        self.mock_log = self.patcher_log.start()

        # Set up predictable paths for our core directories
        core.library = "C:/Fake/Library"
        core.archive = "C:/Fake/Archive"
        s.MAIN_DIRECTORY = "C:/Fake/Game/"

    def tearDown(self):
        self.patcher_log.stop()

    @patch('source.modificator.TEST', False)
    @patch('source.modificator.definition_edit')
    @patch('source.modificator.transfer_switch')
    @patch('os.path.isdir')
    @patch('os.mkdir')
    def test_mod_attach__routing_changes(self, mock_mkdir, mock_isdir, mock_transfer, mock_def_edit):
        # 1. Arrange
        # Pretend the library mod folder exists, but the archive folder does NOT
        def isdir_mock(path):
            if "Library/MyMod" in path: return True
            if "Archive/MyMod" in path: return False
            return True

        mock_isdir.side_effect = isdir_mock

        # Construct a fake mod object with various change types
        fake_mod = Mod({
            Property.NAME: "MyMod",
            Property.TRANSFER_TYPE: modificator.DEFINITION_CLASSES[0],  # General (uses MOVE)
            Property.CHANGES: {
                "data/ini/added.ini": [Change.ADDED, "hash1"],
                "data/ini/changed.ini": [Change.CHANGED, "hash2", "hash3"],
                "data/ini/removed.ini": [Change.REMOVED, "hash4"],
                "data/ini/unchanged.ini": [Change.UNCHANGED, "hash5"]
            }
        })

        # Mock out the relative checks to isolate just this mod's routing
        with patch('source.modificator.mod_detect_override', return_value=False), \
                patch('source.modificator.mod_check_relative', return_value=False):

            # 2. Act
            # We use check_type='pass' to bypass the active status check for this test
            result = modificator.mod_attach(mod_object=fake_mod, check_type='pass')

        # 3. Assert
        self.assertTrue(result)
        mock_mkdir.assert_called_once_with("C:/Fake/Archive/MyMod")

        # Verify the exact routing of files!
        # ADDED files move from Library to Game
        mock_transfer.assert_any_call(
            "C:/Fake/Library/MyMod/data/ini/added.ini",
            "C:/Fake/Game/data/ini",
            Transfer.MOVE, False
        )

        # CHANGED files move Source -> Archive, THEN Mod -> Game
        mock_transfer.assert_any_call(
            "C:/Fake/Game/data/ini/changed.ini",
            "C:/Fake/Archive/MyMod/data/ini",
            Transfer.MOVE, False
        )
        mock_transfer.assert_any_call(
            "C:/Fake/Library/MyMod/data/ini/changed.ini",
            "C:/Fake/Game/data/ini",
            Transfer.MOVE, False
        )

        # REMOVED files move from Source -> Archive
        mock_transfer.assert_any_call(
            "C:/Fake/Game/data/ini/removed.ini",
            "C:/Fake/Archive/MyMod/data/ini",
            Transfer.MOVE, False
        )

        # UNCHANGED files should trigger ZERO transfers
        for call_args in mock_transfer.call_args_list:
            self.assertNotIn("unchanged.ini", call_args[0][0])

        # Verify the mod is set to Active at the very end
        mock_def_edit.assert_called_with(definition_object=fake_mod, active=True)

    @patch('source.modificator.TEST', False)
    @patch('source.modificator.mod_reverse')
    @patch('source.modificator.transfer_switch')
    @patch('os.path.isdir', return_value=True)
    def test_mod_attach__cancellation_on_error(self, mock_isdir, mock_transfer, mock_reverse):
        # 1. Arrange
        fake_mod = Mod({
            Property.NAME: "MyMod",
            Property.TRANSFER_TYPE: modificator.DEFINITION_CLASSES[0],
            Property.CHANGES: {"data/ini/added.ini": [Change.ADDED, "hash1"]}
        })

        # Force transfer_switch to crash, simulating a file lock or permissions error
        mock_transfer.side_effect = s.InternalError("File is locked")

        with patch('source.modificator.mod_detect_override', return_value=False), \
                patch('source.modificator.mod_check_relative', return_value=False):
            # 2. Act
            result = modificator.mod_attach(mod_object=fake_mod, check_type='pass')

        # 3. Assert
        self.assertFalse(result)

        # Verify it successfully caught the error and triggered a rollback
        mock_reverse.assert_called_once_with(mod_object=fake_mod, transfer=Transfer.REMOVE, check_type='pass')

        # Verify the log noted the cancellation
        logged_messages = "".join(call.args[0] for call in self.mock_log.call_args_list)
        self.assertIn("CANCELLED", logged_messages)


class Test_Modificator_Reverse(unittest.TestCase):

    def setUp(self):
        # Prevent actual logging
        self.patcher_log = patch('source.modificator.log')
        self.mock_log = self.patcher_log.start()

        # Set up predictable paths
        core.library = "C:/Fake/Library"
        core.archive = "C:/Fake/Archive"
        s.MAIN_DIRECTORY = "C:/Fake/Game"

    def tearDown(self):
        self.patcher_log.stop()

    @patch('source.modificator.TEST', False)
    @patch('source.modificator.definition_edit')
    @patch('source.modificator.transfer_switch')
    @patch('os.path.isdir')
    @patch('os.mkdir')
    def test_mod_reverse__routing_changes(self, mock_mkdir, mock_isdir, mock_transfer, mock_def_edit):
        # 1. Arrange
        # Pretend the library mod folder does NOT exist so os.mkdir gets called
        mock_isdir.return_value = False

        fake_mod = Mod({
            Property.NAME: "MyMod",
            Property.ACTIVE: True,
            Property.TRANSFER_TYPE: modificator.DEFINITION_CLASSES[0],  # General class
            Property.CHANGES: {
                "data/ini/added.ini": [Change.ADDED, "hash1"],
                "data/ini/changed.ini": [Change.CHANGED, "hash2", "hash3"],
                "data/ini/removed.ini": [Change.REMOVED, "hash4"],
                "data/ini/unchanged.ini": [Change.UNCHANGED, "hash5"]
            }
        })

        # Mock out relative checks to isolate just this mod's routing
        with patch('source.modificator.mod_check_relative', return_value=False):
            # 2. Act
            # Transfer.REMOVE on a General class automatically translates to Transfer.MOVE
            result = modificator.mod_reverse(
                mod_object=fake_mod,
                transfer=Transfer.REMOVE,
                check_type='pass'
            )

        # 3. Assert
        self.assertTrue(result)
        mock_mkdir.assert_called_once_with("C:/Fake/Library/MyMod")

        # Verify the exact routing of files!

        # ADDED files move from Source (Game) -> Mod (Library)
        mock_transfer.assert_any_call(
            "C:/Fake/Game/data/ini/added.ini",
            "C:/Fake/Library/MyMod/data/ini",
            Transfer.MOVE, False
        )

        # CHANGED files move Source -> Mod, THEN Archive -> Game
        mock_transfer.assert_any_call(
            "C:/Fake/Game/data/ini/changed.ini",
            "C:/Fake/Library/MyMod/data/ini",
            Transfer.MOVE, False
        )
        mock_transfer.assert_any_call(
            "C:/Fake/Archive/MyMod/data/ini/changed.ini",
            "C:/Fake/Game/data/ini",
            Transfer.MOVE, False
        )

        # REMOVED files move Archive -> Game
        mock_transfer.assert_any_call(
            "C:/Fake/Archive/MyMod/data/ini/removed.ini",
            "C:/Fake/Game/data/ini",
            Transfer.MOVE, False
        )

        # UNCHANGED files should trigger ZERO transfers
        for call_args in mock_transfer.call_args_list:
            self.assertNotIn("unchanged.ini", call_args[0][0])

        # Verify the mod is deactivated at the end
        mock_def_edit.assert_called_with(definition_object=fake_mod, active=False)

    @patch('source.modificator.TEST', False)
    @patch('source.modificator.mod_attach')
    @patch('source.modificator.transfer_switch')
    @patch('os.path.isdir', return_value=True)
    def test_mod_reverse__cancellation_on_error(self, mock_isdir, mock_transfer, mock_attach):
        # 1. Arrange
        fake_mod = Mod({
            Property.NAME: "MyMod",
            Property.ACTIVE: True,
            Property.TRANSFER_TYPE: modificator.DEFINITION_CLASSES[0],
            Property.CHANGES: {"data/ini/added.ini": [Change.ADDED, "hash1"]}
        })

        # Force a failure during the transfer
        mock_transfer.side_effect = s.InternalError("Access Denied")

        with patch('source.modificator.mod_check_relative', return_value=False):
            # 2. Act
            result = modificator.mod_reverse(
                mod_object=fake_mod,
                transfer=Transfer.REMOVE,
                check_type='pass'
            )

        # 3. Assert
        self.assertFalse(result)

        # Verify the rollback mechanism kicked in to re-attach the mod
        mock_attach.assert_called_once_with(
            mod_directory="C:/Fake/Library/MyMod",
            check_type='pass'
        )

        # Verify the cancellation was logged
        logged_messages = "".join(call.args[0] for call in self.mock_log.call_args_list)
        self.assertIn("CANCELLED", logged_messages)


class Test_Modificator_Helpers(unittest.TestCase):

    def setUp(self):
        # Set a predictable library path for path-slicing tests
        core.library = "C:/Fake/Library"

    # --- 1. Path Generation (ensure_path_exists) ---

    @patch('os.makedirs')
    @patch('os.mkdir')
    @patch('os.path.exists')
    def test_ensure_path_exists__standard(self, mock_exists, mock_mkdir, mock_makedirs):
        # Pretend no directories exist yet
        mock_exists.return_value = False

        # Test standard relative directory creation
        modificator.ensure_path_exists("C:/Fake/Dir/file.txt", check_path="C:/Fake/Base")

        # It should make the base dir, and then create the subdirectories
        mock_makedirs.assert_called_with("C:/Fake/Base", exist_ok=True)
        mock_mkdir.assert_called_with("C:/Fake/Base/Dir")

    @patch('os.makedirs')
    @patch('os.mkdir')
    @patch('os.path.exists')
    def test_ensure_path_exists__with_library(self, mock_exists, mock_mkdir, mock_makedirs):
        mock_exists.return_value = False

        # Pass a path that includes the core library
        test_path = f"{core.library}/MyMod/data/ini/file.txt"
        modificator.ensure_path_exists(test_path)

        # It should automatically extract "MyMod" as the base path and step through the rest
        mock_makedirs.assert_called_with("C:/Fake/Library/MyMod", exist_ok=True)
        mock_mkdir.assert_any_call("C:/Fake/Library/MyMod/data")
        mock_mkdir.assert_any_call("C:/Fake/Library/MyMod/data/ini")

    # --- 2. Hashing Engine (hash_file) ---

    @patch('source.modificator.xxhash')
    @patch('builtins.open', new_callable=mock_open, read_data=b"binary_data")
    def test_hash_file(self, mock_file, mock_xxhash):
        # Setup a mock return for the xxhash algorithm
        mock_xxhash_instance = MagicMock()
        mock_xxhash_instance.hexdigest.return_value = "fake_hash_123"
        mock_xxhash.xxh128.return_value = mock_xxhash_instance

        result = modificator.hash_file("dummy.txt")

        # Verify it opened the file in 'rb' (read-binary) mode
        mock_file.assert_called_once_with("dummy.txt", 'rb')
        mock_xxhash.xxh128.assert_called_once_with(b"binary_data")
        self.assertEqual(result, "fake_hash_123")

    # --- 3. Dependency Logic (check_library) ---

    @patch('os.path.isfile')
    def test_check_library(self, mock_isfile):
        fake_mod = Mod({
            Property.NAME: "MyMod",
            Property.CHANGES: {"file1.txt": [], "file2.txt": []}
        })

        # Scenario 1: Both files exist in the library
        mock_isfile.return_value = True
        self.assertFalse(modificator.check_library(fake_mod))

        # Scenario 2: One file is missing from the library folder
        mock_isfile.side_effect = lambda path: "file1" in path
        self.assertTrue(modificator.check_library(fake_mod))

    # --- 4. Relative Link Checkers ---

    @patch('source.modificator.definition_read')
    @patch('os.path.isfile')
    def test_mod_check_relative__overrode_by(self, mock_isfile, mock_def_read):
        mock_isfile.return_value = True
        fake_mod = Mod({Property.OVERRODE_BY: "ChildMod"})
        fake_child = Mod({Property.ACTIVE: True})
        mock_def_read.return_value = fake_child

        result = modificator.mod_check_relative(fake_mod, Property.OVERRODE_BY)

        # If checking heirs (OVERRODE_BY), it only returns the mod if it is ACTIVE
        mock_def_read.assert_called_once_with(f"{core.library}/ChildMod")
        self.assertEqual(result, fake_child)

    @patch('source.modificator.definition_read')
    @patch('os.path.isfile')
    def test_mod_check_relative__overrides(self, mock_isfile, mock_def_read):
        mock_isfile.return_value = True
        fake_mod = Mod({Property.OVERRIDES: "ParentMod"})
        fake_parent = Mod({Property.ACTIVE: False})
        mock_def_read.return_value = fake_parent

        result = modificator.mod_check_relative(fake_mod, Property.OVERRIDES)

        # If checking ancestors (OVERRIDES), it only returns the mod if it is INACTIVE
        mock_def_read.assert_called_once_with(mod_path=f"{core.library}/ParentMod")
        self.assertEqual(result, fake_parent)

    @patch('source.modificator.mods_select')
    def test_mod_detect_override(self, mock_mods_select):
        fake_active_mod = Mod({
            Property.NAME: "ActiveMod",
            Property.OVERRODE_BY: "",
            Property.CHANGES: {"data/file.txt": []}
        })
        mock_mods_select.return_value = [fake_active_mod]

        # Match 1: Explicitly defining the override parent
        fake_mod_explicit = Mod({Property.OVERRIDES: "ActiveMod", Property.CHANGES: {}})
        self.assertEqual(modificator.mod_detect_override(fake_mod_explicit), fake_active_mod)

        # Match 2: Implicit match by overlapping changed files
        fake_mod_implicit = Mod({Property.OVERRIDES: "", Property.CHANGES: {"data/file.txt": []}})
        self.assertEqual(modificator.mod_detect_override(fake_mod_implicit), fake_active_mod)

        # Match 3: No relation at all
        fake_mod_no_match = Mod({Property.OVERRIDES: "OtherMod", Property.CHANGES: {"data/other.txt": []}})
        self.assertFalse(modificator.mod_detect_override(fake_mod_no_match))


if __name__ == '__main__':
    unittest.main()
