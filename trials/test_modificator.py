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

        result = modificator.definition_read(f"{core.install_path}/Fake/Library/MyMod")

        # Verify it loaded the JSON and converted it into a Mod object
        mock_file.assert_called_once_with(f"{core.install_path}/Fake/Library/MyMod/_definition.json")
        self.assertIsInstance(result, Mod)
        self.assertEqual(result[Property.NAME], "LoadedMod")

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_definition_save(self, mock_json_dump, mock_file):
        dummy_mod = Mod({Property.NAME: "SaveMe"})

        modificator.definition_save(dummy_mod, f"{core.install_path}/Fake/Library/SaveMe")

        # Verify it wrote to the correct file path using json.dump
        mock_file.assert_called_once_with(f"{core.install_path}/Fake/Library/SaveMe/_definition.json", 'w')
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


class Test_Modificator_Attach(unittest.TestCase):

    def setUp(self):
        # Prevent actual logging
        self.patcher_log = patch('source.modificator.log')
        self.mock_log = self.patcher_log.start()

        # Set up predictable paths for our core directories
        core.library = f"{core.install_path}/Fake/Library"
        core.archive = f"{core.install_path}/Fake/Archive"
        s.MAIN_DIRECTORY = f"{core.install_path}/Fake"

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
            if "Library/MyMod" in path:
                return True
            if "Archive/MyMod" in path:
                return False
            return True

        mock_isdir.side_effect = isdir_mock

        # Construct a fake mod object with various change types
        fake_mod = Mod({
            Property.NAME: "MyMod",
            Property.TRANSFER_TYPE: modificator.DEFINITION_CLASSES[0],  # General (uses MOVE)
            Property.CHANGES: {
                "game/data/ini/added.ini": [Change.ADDED, "hash1"],
                "game/data/ini/changed.ini": [Change.CHANGED, "hash2", "hash3"],
                "game/data/ini/removed.ini": [Change.REMOVED, "hash4"],
                "game/data/ini/unchanged.ini": [Change.UNCHANGED, "hash5"]
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
        mock_mkdir.assert_called_once_with(f"{core.install_path}/Fake/Archive/MyMod")

        # Verify the exact routing of files!
        # ADDED files move from Library to Game
        mock_transfer.assert_any_call(
            f"{core.install_path}/Fake/Library/MyMod/game/data/ini/added.ini",
            f"{core.install_path}/game/data/ini",
            Transfer.MOVE, False
        )

        # CHANGED files move Source -> Archive, THEN Mod -> Game
        mock_transfer.assert_any_call(
            f"{core.install_path}/game/data/ini/changed.ini",
            f"{core.install_path}/Fake/Archive/MyMod/game/data/ini",
            Transfer.MOVE, False
        )
        mock_transfer.assert_any_call(
            f"{core.install_path}/Fake/Library/MyMod/game/data/ini/changed.ini",
            f"{core.install_path}/game/data/ini",
            Transfer.MOVE, False
        )

        # REMOVED files move from Source -> Archive
        mock_transfer.assert_any_call(
            f"{core.install_path}/game/data/ini/removed.ini",
            f"{core.install_path}/Fake/Archive/MyMod/game/data/ini",
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
        core.library = f"{core.install_path}/Fake/Library"
        core.archive = f"{core.install_path}/Fake/Archive"
        s.MAIN_DIRECTORY = f"{core.install_path}/Fake"

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
                "Game/data/ini/added.ini": [Change.ADDED, "hash1"],
                "Game/data/ini/changed.ini": [Change.CHANGED, "hash2", "hash3"],
                "Game/data/ini/removed.ini": [Change.REMOVED, "hash4"],
                "Game/data/ini/unchanged.ini": [Change.UNCHANGED, "hash5"]
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
        mock_mkdir.assert_called_once_with(f"{core.install_path}/Fake/Library/MyMod")

        # Verify the exact routing of files!

        # ADDED files move from Source (Game) -> Mod (Library)
        mock_transfer.assert_any_call(
            f"{core.install_path}/Game/data/ini/added.ini",
            f"{core.install_path}/Fake/Library/MyMod/Game/data/ini",
            Transfer.MOVE, False
        )

        # CHANGED files move Source -> Mod, THEN Archive -> Game
        mock_transfer.assert_any_call(
            f"{core.install_path}/Game/data/ini/changed.ini",
            f"{core.install_path}/Fake/Library/MyMod/Game/data/ini",
            Transfer.MOVE, False
        )
        mock_transfer.assert_any_call(
            f"{core.install_path}/Fake/Archive/MyMod/Game/data/ini/changed.ini",
            f"{core.install_path}/Game/data/ini",
            Transfer.MOVE, False
        )

        # REMOVED files move Archive -> Game
        mock_transfer.assert_any_call(
            f"{core.install_path}/Fake/Archive/MyMod/Game/data/ini/removed.ini",
            f"{core.install_path}/Game/data/ini",
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
            mod_directory=f"{core.install_path}/Fake/Library/MyMod",
            check_type='pass'
        )

        # Verify the cancellation was logged
        logged_messages = "".join(call.args[0] for call in self.mock_log.call_args_list)
        self.assertIn("CANCELLED", logged_messages)


class Test_Modificator_Helpers(unittest.TestCase):

    def setUp(self):
        # Set a predictable library path for path-slicing tests
        core.library = f"{core.install_path}/Fake/Library"

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


class Test_Modificator_Snapshots(unittest.TestCase):

    def setUp(self):
        # Prevent actual logging
        self.patcher_log = patch('source.modificator.log')
        self.mock_log = self.patcher_log.start()

        # Predictable paths
        core.library = "C:/Fake/Library"
        core.install_path = "C:/Fake/Install"

        # We need to ensure os.path.abspath returns our fake paths cleanly
        # because snapshot_take uses it to calculate string slices.
        self.patcher_abspath = patch('os.path.abspath', side_effect=lambda p: p)
        self.patcher_abspath.start()

    def tearDown(self):
        self.patcher_log.stop()
        self.patcher_abspath.stop()

    # --- 1. File Name Generator (get_available_name) ---

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

    # --- 2. Snapshot Logic (snapshot_take) ---

    @patch('source.modificator.datetime')
    @patch('source.modificator.hash_directory')
    def test_snapshot_take__provided_paths(self, mock_hash_directory, mock_datetime):
        # Freeze time for a predictable dict output
        mock_datetime.now.return_value = "2023-01-01 12:00:00"

        # Provide a fake hash output
        mock_hash_directory.return_value = {"data/ini/file.txt": "fake_hash"}

        # Test taking a snapshot of a specific game path (bypassing UI prompts)
        result = modificator.snapshot_take(game_paths=["C:/Fake/Game/data"])

        # Verify it passed the install path to be omitted
        mock_hash_directory.assert_called_once_with("C:/Fake/Game/data", path_to_omit="C:/Fake/Install")

        # Verify the returned dictionary shape
        self.assertEqual(result["date"], "2023-01-01 12:00:00")
        self.assertEqual(result["data/ini/file.txt"], "fake_hash")

    @patch('source.modificator.askdirectory')
    @patch('source.modificator.hash_directory')
    def test_snapshot_take__ui_prompt(self, mock_hash_directory, mock_askdirectory):
        mock_hash_directory.return_value = {}

        # The askdirectory prompt is in a while loop. We return a valid path first,
        # then return an empty string "" to simulate the user clicking "Cancel", which breaks the loop.
        mock_askdirectory.side_effect = ["C:/Fake/Install/MyGame", ""]

        modificator.snapshot_take()

        # Verify it asked for a directory and successfully processed the chosen path
        mock_askdirectory.assert_called()
        mock_hash_directory.assert_called_once_with("MyGame", path_to_omit="C:/Fake/Install")

    # --- 3. Snapshot Saving (snapshot_save) ---

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

    # --- 4. Comparison Coordinator (initiate_comparison) ---

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
