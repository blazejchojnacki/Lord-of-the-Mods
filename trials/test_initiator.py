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
            self.assertEqual(core.state.install_path, "C:/install_path")
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

    @patch('source.initiator.os.mkdir')
    @patch('source.initiator.os.path.isdir')
    @patch.object(core.AppConfig, 'save')
    @patch('source.initiator.Mod.create')
    def test_set_directories(self, mock_mod_create, mock_save, mock_isdir, mock_mkdir):
        # 1. Arrange: Pretend no directories exist yet so os.mkdir gets called
        mock_isdir.return_value = False

        # Set up a fake install path so os.path.relpath has something to work with
        core.state.install_path = "C:/Fake/Install/Path"

        # Create our dummy inputs
        dummy_directories = {
            'library': 'C:/Fake/Install/Path/_LIBRARY',
            'archive': 'C:/Fake/Install/Path/_ARCHIVE'
        }
        dummy_games = ['C:/Fake/Install/Path/Game1', 'C:/Fake/Install/Path/Game2']

        # Pretend Mod.create returns a dummy Mod object so we can test if .save() is called on it
        dummy_definition_object = MagicMock()
        mock_mod_create.return_value = dummy_definition_object

        # 2. Act: Call the updated initiator function
        initiator.set_directories(dummy_directories, dummy_games)

        # 3. Assert: Verify the logic worked exactly as expected

        # A. Check that the state was updated and saved with relative paths
        mock_save.assert_called_once_with(
            settings_dict={
                Setting.INSTALL: 'C:/Fake/Install/Path',
                Setting.LIBRARY: '_LIBRARY',
                Setting.ARCHIVE: '_ARCHIVE',
                Setting.GAMES: dummy_games,
            }
        )

        # B. Check that standard root directories were created (Snapshot & Comparison)
        mock_mkdir.assert_any_call(initiator.SNAPSHOT_DIRECTORY)
        mock_mkdir.assert_any_call(initiator.SNAPSHOT_COMPARISON_DIRECTORY)

        # C. Check that Mod.create was called correctly for BOTH games
        self.assertEqual(mock_mod_create.call_count, 2)

        mock_mod_create.assert_any_call(
            name="Game1",
            changes_source=dummy_games[0],
            description="Initial Game1 - created automatically"
        )
        mock_mod_create.assert_any_call(
            name="Game2",
            changes_source=dummy_games[1],
            description="Initial Game2 - created automatically"
        )

        # D. Check that .save() was called on the Mod object for BOTH games
        self.assertEqual(dummy_definition_object.save.call_count, 2)


if __name__ == '__main__':
    unittest.main()
