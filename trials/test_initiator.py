import unittest
from unittest.mock import patch, MagicMock
import os
from pathlib import Path

import source.initiator as initiator
import source.core as core
from source.shared import Setting


class Test_Initiator(unittest.TestCase):

    # --- 1. Test cancel_initiation ---

    @patch('source.initiator.exit')
    @patch('source.initiator.showerror')
    def test_cancel_initiation(self, mock_showerror, mock_exit):
        # Call the function
        initiator.cancel_initiation()

        # Verify it attempts to show an error dialog and then exits the program
        mock_showerror.assert_called_once()
        mock_exit.assert_called_once()

    # --- 2. Test ensure_game_options ---

    @patch('source.initiator.shutil.copy')
    @patch('source.initiator.os.mkdir')
    @patch('source.initiator.os.path.isfile')
    @patch('source.initiator.os.path.isdir')
    def test_ensure_game_options__creates_files(self, mock_isdir, mock_isfile, mock_mkdir, mock_copy):
        # Pretend directories and files do NOT exist, forcing the function to create them
        mock_isdir.return_value = False
        mock_isfile.return_value = False

        # Temporarily mock the game_list to a predictable, single-game state
        original_game_list = initiator.game_list
        initiator.game_list = [{
            "Name": "Test Game",
            "Roaming": "/TestRoaming",
            "RoamingFiles": ["/TestOptions.ini"]
        }]

        try:
            initiator.ensure_game_options()

            # It should have tried to make the roaming directory and copy the file
            mock_mkdir.assert_called_once()
            mock_copy.assert_called_once()
        finally:
            # Restore the original list so we don't break other tests
            initiator.game_list = original_game_list

    @patch('source.initiator.shutil.copy')
    @patch('source.initiator.os.mkdir')
    @patch('source.initiator.os.path.isfile')
    @patch('source.initiator.os.path.isdir')
    def test_ensure_game_options__skips_existing(self, mock_isdir, mock_isfile, mock_mkdir, mock_copy):
        # Pretend everything already exists
        mock_isdir.return_value = True
        mock_isfile.return_value = True

        original_game_list = initiator.game_list
        initiator.game_list = [{"Roaming": "/TestRoaming", "RoamingFiles": ["/TestOptions.ini"]}]

        try:
            initiator.ensure_game_options()

            # Since they exist, mkdir and copy should NEVER be called
            mock_mkdir.assert_not_called()
            mock_copy.assert_not_called()
        finally:
            initiator.game_list = original_game_list

    # --- 3. Test get_game_directory ---

    @patch('source.initiator.os.path.isdir')
    @patch('source.initiator.search_reg')
    def test_get_game_directory__found_in_registry(self, mock_search_reg, mock_isdir):
        # Pretend the registry search works perfectly and returns a path
        mock_search_reg.return_value = "C:/install_path/Game"
        # Pretend the returned path is a valid directory
        mock_isdir.return_value = True

        original_game_list = initiator.game_list
        initiator.game_list = [{"Name": "Test Game", "Registry": "FakeReg"}]

        try:
            directories = initiator.get_game_directory()

            # Verify the function formatted the path relative to the install_path
            self.assertEqual(len(directories), 1)
            self.assertTrue(directories[0].startswith("Game") or directories[0] == "")
            self.assertEqual(str(core.state.install_path), str(Path("C:/install_path").resolve()))
        finally:
            initiator.game_list = original_game_list

    @patch('source.initiator.cancel_initiation')
    @patch('source.initiator.askdirectory')
    @patch('source.initiator.search_reg')
    def test_get_game_directory__not_found_user_cancels(self, mock_search_reg, mock_askdirectory, mock_cancel):
        # Pretend the registry failed
        mock_search_reg.side_effect = FileNotFoundError()
        # Pretend the user hit "Cancel" on the folder dialog (returns empty string)
        mock_askdirectory.return_value = ""

        original_game_list = initiator.game_list
        initiator.game_list = [{"Name": "Test Game", "Registry": "FakeReg"}]

        try:
            initiator.get_game_directory()

            # The function should trigger the cancel_initiation fail-safe
            mock_cancel.assert_called_once()
        finally:
            initiator.game_list = original_game_list

    # ERROR: using definition_save, definition_write
    @patch('source.initiator.definition_save')
    @patch('source.initiator.definition_write')
    @patch('source.core.state.save')
    @patch('source.initiator.os.mkdir')
    @patch('source.initiator.os.path.isdir')
    def test_set_directories(self, mock_isdir, mock_mkdir, mock_settings_save, mock_def_write,
                             mock_def_save):
        # 1. Arrange: Pretend no directories exist yet so os.mkdir gets called
        mock_isdir.return_value = False

        # Set up a fake install path so os.path.relpath has something to work with
        core.state.install_path = "C:/Fake/Install/Path"

        # Create our dummy inputs (what the user *would* have chosen in the UI)
        dummy_directories = {
            'library': 'C:/Fake/Install/Path/_LIBRARY',
            'archive': 'C:/Fake/Install/Path/_ARCHIVE'
        }
        dummy_games = ['C:/Fake/Install/Path/Game1', 'C:/Fake/Install/Path/Game2']

        # Pretend definition_write returns a dummy object
        mock_def_write.return_value = "dummy_definition_object"

        # 2. Act: Call our new purely logical function
        initiator.set_directories(dummy_directories, dummy_games)

        # 3. Assert: Verify the logic worked exactly as expected

        # A. Check that settings.save was called with relative paths
        mock_settings_save.assert_called_once_with(
            settings_dict={
                Setting.LIBRARY: '_LIBRARY',
                Setting.ARCHIVE: '_ARCHIVE',
                Setting.GAMES: dummy_games,
            }
        )

        # B. Check that standard directories were created (Snapshot & Comparison)
        mock_mkdir.assert_any_call(initiator.SNAPSHOT_DIRECTORY)
        mock_mkdir.assert_any_call(initiator.SNAPSHOT_COMPARISON_DIRECTORY)

        # C. Check that the individual mod directories were created for BOTH games
        expected_mod_dir_1 = f"{core.state.install_path}/_LIBRARY/Game1"
        expected_mod_dir_2 = f"{core.state.install_path}/_LIBRARY/Game2"
        mock_mkdir.assert_any_call(expected_mod_dir_1)
        mock_mkdir.assert_any_call(expected_mod_dir_2)

        # D. Check that definition files were written and saved for BOTH games
        self.assertEqual(mock_def_write.call_count, 2)
        self.assertEqual(mock_def_save.call_count, 2)

        # Verify the exact arguments for the first game's definition save
        mock_def_write.assert_any_call(
            mod_directory=expected_mod_dir_1,
            changes_source=dummy_games[0],
            description="Initial Game1 - created automatically"
        )
        mock_def_save.assert_any_call("dummy_definition_object", expected_mod_dir_1)


if __name__ == '__main__':
    unittest.main()
