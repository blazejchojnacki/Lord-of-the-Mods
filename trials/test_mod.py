import unittest
from unittest.mock import patch, mock_open, MagicMock
import json

from source.messaging import InternalError
from source.constants import Property, DEFINITION_CLASSES, Transfer, Change, MOD_DEF_FILE_NAME
from models.mod import Mod, LibraryManager


class Test_Mod(unittest.TestCase):

    def setUp(self):
        # Create a blank slate Mod instance for testing
        self.mod = Mod(
            transfer_type=DEFINITION_CLASSES[0],
            name="TestMod",
            active=False,
            changes={
                "data/changed_file.ini": [Change.CHANGED, "old_hash", "new_hash"],
                "data/added_file.ini": [Change.ADDED, "new_hash"],
                "data/removed_file.ini": [Change.REMOVED, "old_hash"]
            },
            directory="C:/Fake/Library/TestMod"
        )

        # Patch the global state variables accessed by the Mod class
        self.patcher_state = patch('models.mod.core.state')
        self.mock_state = self.patcher_state.start()
        self.mock_state.install_path = "C:/Fake/Install"
        self.mock_state.archive = "C:/Fake/Archive"
        self.mock_state.library = "C:/Fake/Library"
        self.mock_state.exceptions = []

    def tearDown(self):
        self.patcher_state.stop()

    # --- 1. Testing Data Operations ---

    def test_from_dict_to_dict(self):
        """ Tests that serialization to and from JSON dictionaries works perfectly. """
        original_dict = {
            Property.TRANSFER_TYPE: DEFINITION_CLASSES[0],
            Property.NAME: "TestMod",
            Property.GAME: "BFME2",
            Property.LAUNCH: "",
            Property.ACTIVE: True,
            Property.OVERRIDES: "BaseMod",
            Property.OVERRODE_BY: "",
            Property.DESCRIPTION: "A test mod",
            Property.CHANGES: {"file.ini": [Change.ADDED, "hash"]}
        }

        loaded_mod = Mod.from_dict(original_dict, directory="C:/Fake/Library/TestMod")
        self.assertEqual(loaded_mod.name, "TestMod")
        self.assertTrue(loaded_mod.active)

        exported_dict = loaded_mod.to_dict()
        self.assertEqual(original_dict, exported_dict)

    @patch('os.path.isdir', return_value=True)
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save(self, mock_json_dump, mock_file, mock_isdir):
        """ Tests that saving writes the dictionary to the correct file path. """
        self.mod.save()
        mock_file.assert_called_once_with(f"C:/Fake/Library/TestMod/{MOD_DEF_FILE_NAME}", 'w')
        mock_json_dump.assert_called_once_with(self.mod.to_dict(), mock_file(), indent=4)

    # --- 2. Testing the "Plan" Generation ---

    @patch('os.path.isfile', return_value=False)
    def test_generate_attach_plan(self, mock_isfile):
        """ Tests that the attach plan generates the correct routing paths. """
        plan = self.mod.generate_attach_plan()

        # We expect 4 steps based on our setUp changes:
        # 1. Archive the existing file (for CHANGED)
        # 2. Move the mod file to the game (for CHANGED)
        # 3. Move the mod file to the game (for ADDED)
        # 4. Archive the existing file (for REMOVED)
        self.assertEqual(len(plan), 4)

        # Check the exact paths for the ADDED file step
        added_step = next(step for step in plan if 'added_file.ini' in step['src'])
        self.assertEqual(added_step['src'], "C:/Fake/Library/TestMod/data/added_file.ini")
        self.assertEqual(added_step['dst'], "C:/Fake/Install/data")
        self.assertEqual(added_step['type'], Transfer.MOVE)

    @patch('os.path.isfile', return_value=False)
    def test_generate_detach_plan(self, mock_isfile):
        """ Tests that the detach plan correctly routes files back to the library/archive. """
        plan = self.mod.generate_detach_plan(Transfer.MOVE)

        # We expect 4 steps for detachment as well
        self.assertEqual(len(plan), 4)

        # Check the exact paths for the ADDED file step (should route back to mod dir)
        added_step = next(step for step in plan if 'added_file.ini' in step['src'])
        self.assertEqual(added_step['src'], "C:/Fake/Install/data/added_file.ini")
        self.assertEqual(added_step['dst'], "C:/Fake/Library/TestMod/data")
        self.assertEqual(added_step['type'], Transfer.MOVE)

    # --- 3. Testing the Execution Engine ---

    @patch('models.mod.transfer_switch')
    def test_execute_transfer_plan(self, mock_transfer_switch):
        """ Tests that the generic executor blindly loops through the plan. """
        dummy_plan = [
            {'src': 'A', 'dst': 'B', 'type': Transfer.MOVE},
            {'src': 'C', 'dst': 'D', 'type': Transfer.COPY}
        ]

        self.mod._execute_transfer_plan(dummy_plan, error_sensitive=True)

        self.assertEqual(mock_transfer_switch.call_count, 2)
        mock_transfer_switch.assert_any_call('A', 'B', Transfer.MOVE, True)
        mock_transfer_switch.assert_any_call('C', 'D', Transfer.COPY, True)

    # --- 4. Testing the Orchestrators (Attach / Detach) ---

    @patch('os.makedirs')
    @patch('os.path.isdir', return_value=True)
    @patch.object(Mod, '_resolve_attach_dependencies')
    @patch.object(Mod, 'generate_attach_plan')
    @patch.object(Mod, '_execute_transfer_plan')
    @patch.object(Mod, 'edit')
    def test_attach__execute(self, mock_edit, mock_execute, mock_generate, mock_resolve, mock_isdir, mock_makedirs):
        """ Tests that attach calls the helpers in the correct order. """
        dummy_plan = [{'src': 'A', 'dst': 'B', 'type': Transfer.MOVE}]
        mock_generate.return_value = dummy_plan

        result = self.mod.attach(check_type='ancestor', dry_run=False)

        self.assertTrue(result)
        mock_resolve.assert_called_once_with('ancestor')
        mock_generate.assert_called_once()
        mock_execute.assert_called_once_with(dummy_plan, True)
        mock_edit.assert_called_once_with(active=True)

    @patch.object(Mod, '_resolve_attach_dependencies')
    @patch.object(Mod, 'generate_attach_plan')
    @patch.object(Mod, '_execute_transfer_plan')
    def test_attach__dry_run(self, mock_execute, mock_generate, mock_resolve):
        """ Tests that dry_run returns the plan directly and aborts execution. """
        dummy_plan = [{'src': 'A', 'dst': 'B', 'type': Transfer.MOVE}]
        mock_generate.return_value = dummy_plan

        # Call with dry_run=True
        result = self.mod.attach(dry_run=True)

        self.assertEqual(result, dummy_plan)
        mock_execute.assert_not_called()  # Execution MUST NOT be called!# --- 5. Testing Utilities and File Checks ---

    @patch.object(Mod, 'save')
    def test_edit(self, mock_save):
        """ Tests that edit updates attributes and auto-saves, but blocks name changes. """
        self.mod.edit(description="Updated description", active=True)
        self.assertEqual(self.mod.description, "Updated description")
        self.assertTrue(self.mod.active)
        mock_save.assert_called_once()

        # Ensure it raises an error if we try to change the name directly
        self.assertRaises(InternalError, self.mod.edit, name="NewName")

    @patch('os.path.isfile')
    def test_check_library(self, mock_isfile):
        """ Tests the detection of missing files in the library. """
        # Pretend the removed file is missing, but others are there
        def fake_isfile(path):
            if "removed_file.ini" in path: return False
            return True
        mock_isfile.side_effect = fake_isfile

        # It should return True because a file is missing
        self.assertTrue(self.mod.check_library())

    @patch('source.modificator.hash_file')
    @patch('os.path.isfile', return_value=True)
    def test_detect_changes(self, mock_isfile, mock_hash_file):
        """ Tests the hash comparison logic to see if files were modified externally. """
        # Let's pretend hash_file returns "new_hash" for the changed file,
        # but something completely different for the added file
        def fake_hash(path):
            if "changed_file.ini" in path: return "new_hash"
            if "added_file.ini" in path: return "unexpected_tampered_hash"
            return "old_hash"
        mock_hash_file.side_effect = fake_hash

        changes = self.mod.detect_changes()

        # 'changed_file.ini' is perfectly fine (matches the expected new_hash)
        self.assertNotIn("data/changed_file.ini", changes)

        # 'added_file.ini' was tampered with!
        self.assertIn("data/added_file.ini", changes)
        self.assertEqual(changes["data/added_file.ini"][0], Change.CHANGED)

    @patch.object(Mod, 'detach')
    @patch.object(Mod, 'attach')
    def test_wrappers(self, mock_attach, mock_detach):
        """ Tests that retrieve, extract, and reload call detach/attach correctly. """
        mock_detach.return_value = True
        mock_attach.return_value = True

        self.mod.retrieve()
        mock_detach.assert_called_with(transfer=Transfer.REMOVE)

        self.mod.extract()
        mock_detach.assert_called_with(transfer=Transfer.COPY)

        self.mod.reload()
        mock_detach.assert_called_with(transfer=Transfer.REMOVE)
        mock_attach.assert_called_once()


class Test_LibraryManager(unittest.TestCase):

    @patch('os.listdir', return_value=["ModA", "ModB"])
    @patch('models.mod.core.state')
    @patch.object(Mod, 'load')
    def test_get_all_mods(self, mock_mod_load, mock_state, mock_listdir):
        """ Tests that the library manager successfully loads definitions from folders. """
        mock_state.library = "C:/Fake/Library"
        mock_state.exceptions = []

        mock_mod_load.side_effect = [MagicMock(name="ModA"), MagicMock(name="ModB")]

        mods = LibraryManager.get_all_mods()

        self.assertEqual(len(mods), 2)
        mock_mod_load.assert_any_call("C:/Fake/Library/ModA")
        mock_mod_load.assert_any_call("C:/Fake/Library/ModB")

    @patch.object(LibraryManager, 'get_all_mods')
    def test_select_mods(self, mock_get_all):
        """ Tests that the library manager correctly filters mods by kwargs. """
        mod1 = MagicMock(name="Mod1", transfer_type=DEFINITION_CLASSES[0], active=True, game="BFME")
        mod2 = MagicMock(name="Mod2", transfer_type=DEFINITION_CLASSES[1], active=False, game="BFME")
        mod3 = MagicMock(name="Mod3", transfer_type=DEFINITION_CLASSES[0], active=True, game="RotWK")

        mock_get_all.return_value = [mod1, mod2, mod3]

        # Select all active mods
        active_mods = LibraryManager.select_mods(active=True)
        self.assertEqual(len(active_mods), 2)
        self.assertIn(mod1, active_mods)

        # Select active mods specifically for RotWK
        rotwk_active = LibraryManager.select_mods(active=True, game="RotWK")
        self.assertEqual(len(rotwk_active), 1)
        self.assertIn(mod3, rotwk_active)

    def test_sort_mods(self):
        """ Tests the hierarchical sorting logic based on overrides. """
        # ModC overrides ModB, which overrides ModA
        mod_a = MagicMock(name="ModA")
        mod_a.name = "ModA"
        mod_a.overrides = ""

        mod_b = MagicMock(name="ModB")
        mod_b.name = "ModB"
        mod_b.overrides = "ModA"

        mod_c = MagicMock(name="ModC")
        mod_c.name = "ModC"
        mod_c.overrides = "ModB"

        mods_list = [mod_a, mod_b, mod_c]

        sorted_dict = LibraryManager.sort_mods(Property.OVERRIDES, mods_list)

        # ModA is overridden by ModB (index 1)
        self.assertEqual(sorted_dict["ModA"], "1")
        # ModB is overridden by ModC (index 2)
        self.assertEqual(sorted_dict["ModB"], "2")

    @patch('os.path.isfile', return_value=True)
    @patch.object(Mod, 'load')
    def test_check_relative(self, mock_mod_load, mock_isfile):
        """ Tests resolving ancestor and heir relationships. """
        base_mod = MagicMock(overrides="AncestorMod", overrode_by="HeirMod")

        # Pretend loading the ancestor returns an inactive mod
        mock_ancestor = MagicMock(active=False)
        mock_mod_load.return_value = mock_ancestor

        result = LibraryManager.check_relative(base_mod, Property.OVERRIDES)
        self.assertEqual(result, mock_ancestor)

    @patch.object(LibraryManager, 'select_mods')
    def test_detect_override(self, mock_select_mods):
        """ Tests if the library detects file conflicts between active mods. """
        active_mod = MagicMock(name="ActiveMod", overrode_by="")
        active_mod.changes = {"data/conflict.ini": []}

        mock_select_mods.return_value = [active_mod]

        # 1. Test Explicit Override Match
        new_mod = MagicMock(overrides="ActiveMod", changes={})
        self.assertEqual(LibraryManager.detect_override(new_mod), active_mod)

        # 2. Test File Collision Match
        new_mod = MagicMock(overrides="", changes={"data/conflict.ini": []})
        self.assertEqual(LibraryManager.detect_override(new_mod), active_mod)

        # 3. Test No Collision
        safe_mod = MagicMock(overrides="", changes={"data/safe.ini": []})
        self.assertIsNone(LibraryManager.detect_override(safe_mod))

    @patch('os.rename')
    @patch('os.listdir')
    @patch.object(Mod, 'load')
    @patch.object(Mod, 'save')
    def test_rename_mod(self, mock_save, mock_load, mock_listdir, mock_rename):
        """ Tests that renaming a mod updates its path and fixes sibling links. """
        # Set up a target mod and a sibling that depends on it
        target_mod = Mod(name="OldName", directory="C:/Fake/OldName")
        sibling_mod = MagicMock(name="Sibling", overrides="OldName", overrode_by="")

        # The library contains our old mod and the sibling
        mock_listdir.return_value = ["OldName", "Sibling"]
        mock_load.return_value = sibling_mod

        result = LibraryManager.rename_mod(target_mod, "NewName")

        # 1. Check the target mod was updated
        self.assertEqual(result.name, "NewName")
        self.assertEqual(result.directory, "C:/Fake/NewName")

        # 2. Check the OS was asked to rename the folder
        mock_rename.assert_called_once_with(src="C:/Fake/OldName", dst="C:/Fake/NewName")

        # 3. Check the sibling's links were updated
        sibling_mod.edit.assert_called_once_with(overrides="NewName")


if __name__ == '__main__':
    unittest.main()
