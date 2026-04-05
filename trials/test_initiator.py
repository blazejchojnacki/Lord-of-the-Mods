import unittest
from unittest.mock import patch, MagicMock
import os

from source.constants import Setting
import source.initiator as initiator


class Test_Initiator(unittest.TestCase):

    def setUp(self):
        # Patch the global state used throughout initiator
        self.patcher_state = patch('source.initiator.core.state')
        self.mock_state = self.patcher_state.start()
        self.mock_state.install_path = "C:/Fake/Install"

        # We override the game list in the module so it uses a predictable test set
        self.original_game_list = initiator.game_list
        initiator.game_list = [
            {
                "Name": "Test Game",
                "Registry": "SOFTWARE\\Fake\\Registry",
                "Roaming": "/AppData/Roaming/Test Game",
                "RoamingFiles": ["Options.ini"],
                "EXE": "testgame.exe"
            }
        ]

    def tearDown(self):
        self.patcher_state.stop()
        initiator.game_list = self.original_game_list

    # --- 1. Testing Registry Search ---

    @patch('source.initiator.winreg')
    def test_search_reg(self, mock_winreg):
        """ Tests that it successfully queries the Windows registry and cleans the path. """
        # 1. Setup the mocks to simulate finding the target game key
        mock_master_key = MagicMock()
        mock_child_key = MagicMock()

        mock_winreg.OpenKey.side_effect = [mock_master_key, mock_child_key]
        mock_winreg.QueryInfoKey.return_value = (1,)  # Simulate 1 subkey
        mock_winreg.EnumKey.return_value = "Test Game"  # The name of the subkey matches!

        # Simulate returning a path with a trailing backslash that needs cleaning
        mock_winreg.QueryValueEx.return_value = ("C:\\Fake\\Registry\\Path\\", 1)

        result = initiator.search_reg("SOFTWARE\\Fake", "Test Game")

        # 2. Assertions
        # It should replace backslashes with forward slashes and strip the trailing slash
        self.assertEqual(result, "C:/Fake/Registry/Path")
        mock_winreg.OpenKey.assert_any_call(mock_winreg.ConnectRegistry(), "SOFTWARE\\Fake")
        mock_winreg.QueryValueEx.assert_called_once_with(mock_child_key, 'InstallPath')

    @patch('source.initiator.winreg')
    def test_search_reg_not_found(self, mock_winreg):
        """ Tests that it safely returns an empty string if it gets a PermissionError. """
        mock_winreg.OpenKey.side_effect = PermissionError("Access Denied")
        result = initiator.search_reg("SOFTWARE\\Secure", "Hidden Game")
        self.assertEqual(result, "")

    # --- 2. Testing Setup Operations ---

    @patch('source.initiator.shutil.copy')
    @patch('os.path.isfile', return_value=False)
    @patch('os.mkdir')
    @patch('os.path.isdir', return_value=False)
    @patch('os.path.expanduser')
    def test_ensure_game_options(self, mock_expand, mock_isdir, mock_mkdir, mock_isfile, mock_copy):
        """ Tests that the fallback Roaming folders and Option.ini files are copied correctly. """
        mock_expand.return_value = "C:/Users/FakeUser/AppData/Roaming/Test Game"

        initiator.ensure_game_options()

        # It should create the missing Roaming directory
        mock_mkdir.assert_called_once_with("C:/Users/FakeUser/AppData/Roaming/Test Game")

        # It should attempt to copy the initial Options.ini
        mock_copy.assert_called_once()
        args, kwargs = mock_copy.call_args
        self.assertTrue(args[0].endswith("/initial/Test Game/Options.ini"))
        self.assertEqual(args[1], "C:/Users/FakeUser/AppData/Roaming/Test Game")

    def test_set_directories(self):
        """ Tests that directories are converted to relative paths and saved to state. """
        directories_dict = {
            'library': "C:/Fake/Install/_LIBRARY",
            'archive': "C:/Fake/Install/_ARCHIVE"
        }
        game_paths = ["Game1", "Game2"]

        # Note: core.state.install_path is already set to "C:/Fake/Install" in setUp()
        initiator.set_directories(directories_dict, game_paths)

        # Confirm the paths were made relative
        self.assertEqual(directories_dict['library'], "_LIBRARY")
        self.assertEqual(directories_dict['archive'], "_ARCHIVE")

        # Confirm state was saved with the correct mapping
        self.mock_state.save.assert_called_once_with({
            Setting.INSTALL: "C:/Fake/Install",
            Setting.LIBRARY: "_LIBRARY",
            Setting.ARCHIVE: "_ARCHIVE",
            Setting.GAMES: ["Game1", "Game2"]
        })

    # --- 3. Testing the Main Logic Orchestrator ---

    @patch('source.initiator.ensure_game_options')
    @patch('source.initiator.Mod.create')
    @patch('os.mkdir')
    @patch('os.path.isdir', return_value=False)
    @patch('source.initiator.set_directories')
    def test_execute_initiation(self, mock_set_dirs, mock_isdir, mock_mkdir, mock_create, mock_options):
        """ Tests the end-to-end flow of calculating root paths and building the baseline mods. """
        # Mock inputs
        absolute_game_paths = ["C:/Fake/Games/BFME2", "C:/Fake/Games/RotWK"]
        absolute_directories_dict = {"library": "C:/Fake/Games/_LIBRARY", "archive": "C:/Fake/Games/_ARCHIVE"}

        # Because Path resolution strips slashes differently on Windows vs Linux,
        # we will patch Path to return a consistent dummy object for the test
        with patch('source.initiator.Path') as mock_path:
            mock_resolved = MagicMock()
            mock_resolved.__str__.return_value = "C:/Fake/Games"
            mock_path.return_value.parent.resolve.return_value = mock_resolved

            initiator.execute_initiation(absolute_game_paths, absolute_directories_dict)

        # 1. State should have extracted the shared install path
        self.assertEqual(self.mock_state.install_path, "C:/Fake/Games")

        # 2. It should have calculated relative game paths and passed them to set_directories
        expected_rel_games = ["BFME2", "RotWK"]
        mock_set_dirs.assert_called_once_with(absolute_directories_dict, expected_rel_games)

        # 3. Core directories should have been created
        self.assertEqual(mock_mkdir.call_count, 2)

        # 4. Two base Mods should have been created
        self.assertEqual(mock_create.call_count, 2)
        mock_create.assert_any_call(name="BFME2", changes_source="BFME2",
                                    description="Initial BFME2 - created automatically")
        mock_create.assert_any_call(name="RotWK", changes_source="RotWK",
                                    description="Initial RotWK - created automatically")

        # 5. Fallback options should be triggered
        mock_options.assert_called_once()


if __name__ == '__main__':
    unittest.main()
