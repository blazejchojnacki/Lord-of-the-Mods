import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import os
import json

from models.mod import Mod, LibraryManager
import source.core as core
import source.shared as s
from source.modificator import Property, Transfer, Change, DEFINITION_CLASSES


class Test_Mod_Data_IO(unittest.TestCase):

    def setUp(self):
        self.patcher_log = patch('models.mod.log')
        self.mock_log = self.patcher_log.start()
        core.library = "C:/Fake/Library"
        core.exceptions = ["_ignore_me"]

    def tearDown(self):
        self.patcher_log.stop()

    def test_from_dict_and_to_dict(self):
        # 1. Arrange: A sample dictionary resembling your JSON format
        raw_data = {
            Property.TRANSFER_TYPE: "General",
            Property.NAME: "MyMod",
            Property.GAME: "RotWK",
            Property.ACTIVE: True,
            Property.CHANGES: {"data/ini/file.ini": [Change.ADDED, "hash123"]}
        }

        # 2. Act: Load into object
        my_mod = Mod.from_dict(raw_data, directory="C:/Fake/Dir")

        # 3. Assert: Verify object properties
        self.assertEqual(my_mod.name, "MyMod")
        self.assertTrue(my_mod.active)
        self.assertEqual(my_mod.directory, "C:/Fake/Dir")
        self.assertIn("data/ini/file.ini", my_mod.changes)

        # 4. Act & Assert: Convert back to dict and verify match
        output_dict = my_mod.to_dict()
        self.assertEqual(output_dict[Property.NAME], "MyMod")
        self.assertTrue(output_dict[Property.ACTIVE])

    @patch('models.mod.initiate_comparison')
    @patch('os.mkdir')
    @patch('os.path.isdir')
    @patch.object(Mod, 'save')  # Prevent actual saving to disk during test
    def test_create(self, mock_save, mock_isdir, mock_mkdir, mock_init_comp):
        mock_isdir.return_value = False
        mock_init_comp.return_value = (False, {"data/file.txt": [Change.ADDED, "hash"]})

        new_mod = Mod.create("NewTestMod", changes_source="directory")

        # Verify physical directory was created
        mock_mkdir.assert_called_once_with("C:/Fake/Library/NewTestMod")
        # Verify the comparison logic was triggered
        mock_init_comp.assert_called_once_with("C:/Fake/Library/NewTestMod", changes_source="directory")
        # Verify the object was populated correctly
        self.assertEqual(new_mod.name, "NewTestMod")
        self.assertEqual(new_mod.transfer_type, DEFINITION_CLASSES[0])
        self.assertFalse(new_mod.active)
        # Verify it auto-saved
        mock_save.assert_called_once()

    @patch('os.path.isfile', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data='{"name": "LoadedMod", "active": true}')
    def test_load_and_save(self, mock_file, mock_isfile):
        # Test Load
        loaded_mod = Mod.load("C:/Fake/Library/LoadedMod")
        mock_file.assert_called_with("C:/Fake/Library/LoadedMod/_definition.json", 'r')
        self.assertEqual(loaded_mod.name, "LoadedMod")
        self.assertTrue(loaded_mod.active)

        # Test Save
        loaded_mod.save()
        mock_file.assert_called_with("C:/Fake/Library/LoadedMod/_definition.json", 'w')

    def test_edit(self):
        mod = Mod(name="TestMod", active=False, description="Old")

        # Test standard property edit
        with patch.object(mod, 'save') as mock_save:
            mod.edit(active=True, description="New")
            self.assertTrue(mod.active)
            self.assertEqual(mod.description, "New")
            mock_save.assert_called_once()

        # Test safety block on renaming
        with self.assertRaises(s.InternalError):
            mod.edit(name="NewName")


class Test_Mod_Capabilities(unittest.TestCase):

    def setUp(self):
        self.patcher_log = patch('models.mod.log')
        self.patcher_log.start()

        core.library = "C:/Fake/Library"
        core.archive = "C:/Fake/Archive"
        core.install_path = "C:/Fake/Install"
        s.MAIN_DIRECTORY = "C:/Fake/Install"

    def tearDown(self):
        self.patcher_log.stop()

    @patch('source.modificator.hash_file')
    @patch('os.path.isfile')
    def test_detect_changes(self, mock_isfile, mock_hash_file):
        mock_isfile.return_value = True

        mod = Mod(
            name="MyMod",
            active=True,
            changes={"data/ini/file.txt": [Change.CHANGED, "old_hash_123"]}
        )

        # Scenario 1: Hash perfectly matches expected "old_hash" (no new changes)
        mock_hash_file.return_value = "old_hash_123"
        self.assertEqual(mod.detect_changes(), {})

        # Scenario 2: Hash is different from expected
        mock_hash_file.return_value = "NEW_hash_999"
        detected = mod.detect_changes()
        self.assertIn("data/ini/file.txt", detected)
        self.assertEqual(detected["data/ini/file.txt"][0], Change.CHANGED)
        self.assertEqual(detected["data/ini/file.txt"][1], "NEW_hash_999")

    @patch('source.modificator.transfer_switch')  # Patch the local import
    @patch('os.makedirs')
    @patch('os.path.isdir')
    @patch.object(LibraryManager, 'detect_override', return_value=None)
    @patch.object(LibraryManager, 'check_relative', return_value=None)
    @patch.object(Mod, 'edit')
    def test_attach_and_detach(self, mock_edit, mock_check, mock_detect, mock_isdir, mock_makedirs, mock_transfer):
        mock_isdir.return_value = True

        mod = Mod(
            name="MyMod",
            directory="C:/Fake/Library/MyMod",
            active=False,
            transfer_type=DEFINITION_CLASSES[0],  # General (MOVE)
            changes={
                "data/ini/added.txt": [Change.ADDED, "hash1"],
                "data/ini/changed.txt": [Change.CHANGED, "hash2", "hash3"]
            }
        )

        # Test Attach
        result = mod.attach(check_type='pass')
        self.assertTrue(result)

        # Verify routing logic fired for added files
        mock_transfer.assert_any_call(
            "C:/Fake/Library/MyMod/data/ini/added.txt",
            "C:/Fake/Install/data/ini",
            Transfer.MOVE, False
        )
        # Verify active=True was set
        mock_edit.assert_called_with(active=True)

        # Test Detach
        mock_transfer.reset_mock()
        mock_edit.reset_mock()
        mod.active = True  # Simulate attached state

        result_detach = mod.detach(transfer=Transfer.REMOVE, check_type='pass')
        self.assertTrue(result_detach)

        # Verify it routed back to library
        mock_transfer.assert_any_call(
            "C:/Fake/Install/data/ini/added.txt",
            "C:/Fake/Library/MyMod/data/ini",
            Transfer.MOVE, False
        )
        mock_edit.assert_called_with(active=False)


class Test_LibraryManager(unittest.TestCase):

    def setUp(self):
        core.library = "C:/Fake/Library"
        core.exceptions = ["_ignore_me"]

    @patch('os.listdir')
    @patch.object(Mod, 'load')
    def test_get_all_mods(self, mock_mod_load, mock_listdir):
        mock_listdir.return_value = ["ModA", "ModB", "_ignore_me"]

        # We simulate ModA loading successfully, and ModB throwing an error (e.g. no definition file)
        def mock_load_side_effect(path):
            if "ModA" in path: return Mod(name="ModA")
            raise s.InternalError("No definition")

        mock_mod_load.side_effect = mock_load_side_effect

        result = LibraryManager.get_all_mods()

        # It should ignore "_ignore_me" (exception list) and "ModB" (failed load), leaving only 1
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "ModA")

    @patch.object(LibraryManager, 'get_all_mods')
    def test_select_mods(self, mock_get_all):
        mock_get_all.return_value = [
            Mod(name="ActiveMod", transfer_type="General", active=True),
            Mod(name="InactiveMod", transfer_type="General", active=False),
            Mod(name="TemplateMod", transfer_type="Template", active=True)
        ]

        # 1. Test filtering by attributes
        active_only = LibraryManager.select_mods(active=True)
        self.assertEqual(len(active_only), 1)
        self.assertEqual(active_only[0].name, "ActiveMod")

        # 2. Test implicit class filtering (Templates should always be ignored)
        all_generals = LibraryManager.select_mods()
        self.assertEqual(len(all_generals), 2)
        self.assertNotIn("TemplateMod", [m.name for m in all_generals])

    @patch('os.rename')
    @patch('os.listdir')
    @patch.object(Mod, 'load')
    def test_rename_mod(self, mock_mod_load, mock_listdir, mock_rename):
        mock_listdir.return_value = ["SiblingMod"]

        # Setup the target mod to rename
        target_mod = Mod(name="OldName", directory="C:/Fake/Library/OldName")

        # Setup a sibling mod that depends on OldName
        sibling_mod = Mod(name="SiblingMod", overrides="OldName")
        with patch.object(sibling_mod, 'edit') as mock_edit:
            mock_mod_load.return_value = sibling_mod

            # Execute rename
            with patch.object(target_mod, 'save') as mock_target_save:
                result = LibraryManager.rename_mod(target_mod, "NewName")

            # 1. Verify sibling was updated to reflect new ancestor link
            mock_edit.assert_called_once_with(overrides="NewName")

            # 2. Verify physical folder was renamed
            mock_rename.assert_called_once_with(
                src="C:/Fake/Library/OldName",
                dst="C:/Fake/Library/NewName"
            )

            # 3. Verify target mod's internal state updated and saved
            self.assertEqual(target_mod.name, "NewName")
            self.assertEqual(target_mod.directory, "C:/Fake/Library/NewName")
            mock_target_save.assert_called_once()


if __name__ == '__main__':
    unittest.main()
