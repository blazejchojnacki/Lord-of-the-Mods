import unittest
from unittest.mock import patch, MagicMock
import os
from pathlib import Path

import source.initiator as initiator
import source.core as core


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

            # Verify the function formatted the path relative to the install path
            self.assertEqual(len(directories), 1)
            self.assertTrue(directories[0].startswith("Game") or directories[0] == "")
            self.assertEqual(str(core.install_path), str(Path("C:/install_path").resolve()))
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


if __name__ == '__main__':
    unittest.main()
