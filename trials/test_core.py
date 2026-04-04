import os.path
import unittest
from unittest.mock import patch, mock_open
from pathlib import Path

import source.core as core
import source.shared as shared

TRIALS_PATH = "/".join(str(Path(__file__).parent).split('\\')[-2:])


class Test_AppConfig(unittest.TestCase):
    def setUp(self):
        # We create a fresh, isolated state object for each test! No more global bleeding.
        self.state = core.AppConfig()

        # Capture the default install path to use as our baseline comparison
        self.install_path = core.DEFAULT_INSTALL_PATH
        self.state.install_path = self.install_path

        settings_dict = {
            shared.Setting.TITLE: "Lord of the Mods Settings",
            shared.Setting.VERSION: "",
            shared.Setting.LIBRARY: f"{TRIALS_PATH}/_LIBRARY",
            shared.Setting.ARCHIVE: f"{TRIALS_PATH}/_ARCHIVE",
            shared.Setting.GAMES: ["_GAME1", "_GAME2"],
            shared.Setting.EXCEPTIONS: [f"{TRIALS_PATH}/_LIBRARY/_EXCEPTION"]
        }

        # We target raw_settings instead of treating the object itself like a dict
        self.state.raw_settings = settings_dict

    def test_complete_paths__valid(self):
        settings_dict = {
            shared.Setting.LIBRARY: f"{TRIALS_PATH}/__test_lib",
            shared.Setting.ARCHIVE: f"{TRIALS_PATH}/__test_arch",
            shared.Setting.GAMES: ["game1", "game2"],
            shared.Setting.EXCEPTIONS: [f"{TRIALS_PATH}/__test_lib/__test_not_mod1"]
        }

        # We map against the state's install_path instead of the global core.install_path
        expected_paths = [
            f"{self.install_path}/{TRIALS_PATH}/__test_lib",
            f"{self.install_path}/{TRIALS_PATH}/__test_arch",
            f"{self.install_path}/game1",
            f"{self.install_path}/game2",
            f"{self.install_path}/{TRIALS_PATH}/__test_lib/__test_not_mod1"
        ]

        # complete_paths is now an instance method of AppConfig
        result = self.state.complete_paths(settings_dict)
        self.assertEqual(result, expected_paths)

    def test_complete_paths__empty_library_raises(self):
        settings_dict = {shared.Setting.LIBRARY: ""}
        self.assertRaises(shared.InternalError, self.state.complete_paths, settings_dict)

    def test_complete_paths__empty_archive_raises(self):
        settings_dict = {shared.Setting.ARCHIVE: ""}
        self.assertRaises(shared.InternalError, self.state.complete_paths, settings_dict)

    @patch('os.makedirs')
    def test_create_directories(self, mock_makedirs):
        settings_to_initiate = {
            shared.Setting.LIBRARY: f"{TRIALS_PATH}/__test_lib",
            shared.Setting.ARCHIVE: f"{TRIALS_PATH}/__test_arch",
            shared.Setting.GAMES: [f"{TRIALS_PATH}/__test_game1",
                                   f"{TRIALS_PATH}/__test_game2"],
            shared.Setting.EXCEPTIONS: [f"{TRIALS_PATH}/__test_lib/__test_not_mod1"],
        }
        self.state.create_directories(settings_to_initiate)
        paths = self.state.complete_paths(settings_to_initiate)

        self.assertEqual(mock_makedirs.call_count, 5)
        mock_makedirs.assert_any_call(paths[0], exist_ok=True)
        mock_makedirs.assert_any_call(paths[1], exist_ok=True)

    def test_propagate(self):
        propagated_path_library = f"{TRIALS_PATH}/__test_lib"
        propagated_path_archive = f"{TRIALS_PATH}/__test_arch"
        propagated_paths_games = [f"{TRIALS_PATH}/__test_game1", f"{TRIALS_PATH}/__test_game2"]
        propagated_paths_exceptions = [f"{TRIALS_PATH}/__test_lib/__test_not_mod1"]

        self.state.raw_settings[shared.Setting.LIBRARY] = propagated_path_library
        self.state.raw_settings[shared.Setting.ARCHIVE] = propagated_path_archive
        self.state.raw_settings[shared.Setting.GAMES] = propagated_paths_games
        self.state.raw_settings[shared.Setting.EXCEPTIONS] = propagated_paths_exceptions

        self.state.propagate()

        # We test the object properties directly instead of looking for loose globals
        self.assertEqual(self.state.library, f"{self.install_path}/{propagated_path_library}")
        self.assertEqual(self.state.archive, f"{self.install_path}/{propagated_path_archive}")
        self.assertEqual(self.state.games, [f"{self.install_path}/{_}" for _ in propagated_paths_games])

        # The new logic extracts only the folder name for exceptions
        self.assertEqual(self.state.exceptions, ["__test_not_mod1"])

    @patch('os.path.isfile')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load__existing_file(self, mock_json_load, mock_file, mock_isfile):
        mock_isfile.return_value = True
        mock_json_load.return_value = {
            shared.Setting.LIBRARY: f"{TRIALS_PATH}/__test_lib",
            shared.Setting.ARCHIVE: f"{TRIALS_PATH}/__test_arch",
            shared.Setting.GAMES: [f"{TRIALS_PATH}/__test_game1",
                                   f"{TRIALS_PATH}/__test_game2"],
            shared.Setting.EXCEPTIONS: []
        }

        with patch.object(core.AppConfig, 'propagate') as mock_propagate:
            result = self.state.load()
            self.assertTrue(result)
            self.assertEqual(self.state.raw_settings[shared.Setting.LIBRARY], f"{TRIALS_PATH}/__test_lib")
            mock_propagate.assert_called_once()

    @patch('os.path.isfile')
    def test_load__no_file(self, mock_isfile):
        mock_isfile.return_value = False
        result = self.state.load()

        self.assertFalse(result)
        for key in shared._SETTINGS_FORMAT:
            self.assertIn(key, self.state.raw_settings)

    def test_check_format__missing_key(self):
        if shared.Setting.LIBRARY in self.state.raw_settings:
            self.state.raw_settings.pop(shared.Setting.LIBRARY)
        self.assertRaises(shared.InternalError, self.state.check_format)

    def test_check_format__extra_key(self):
        self.state.raw_settings['unrecognized_key'] = 'test_value'
        self.assertRaises(shared.InternalError, self.state.check_format)

    @patch('os.path.isdir')
    def test_check_paths__existing(self, mock_isdir):
        mock_isdir.return_value = True
        settings_to_check = {
            shared.Setting.LIBRARY: f"{TRIALS_PATH}",
        }
        self.assertTrue(self.state.check_paths(settings_to_check))

    @patch('os.path.isdir')
    def test_check_paths__not_existing(self, mock_isdir):
        mock_isdir.return_value = False
        settings_to_check = {
            shared.Setting.LIBRARY: f"{TRIALS_PATH}/__test_lib",
            shared.Setting.ARCHIVE: f"{TRIALS_PATH}/__test_arch",
        }
        self.assertFalse(self.state.check_paths(settings_to_check))

    def test_check_paths__missing(self):
        settings_to_check = {
            shared.Setting.LIBRARY: "",
        }
        self.assertFalse(self.state.check_paths(settings_to_check))

    @patch.object(core.AppConfig, 'check_paths')
    @patch.object(core.AppConfig, 'check_format')
    @patch.object(core.AppConfig, 'propagate')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save__valid(self, mock_json_dump, mock_file, mock_propagate, mock_check_format, mock_check_paths):
        mock_check_paths.return_value = True
        settings_to_save = {shared.Setting.LIBRARY: f"{TRIALS_PATH}/__test_lib"}

        self.state.save(settings_to_save)

        mock_check_paths.assert_called_once_with(settings_to_save)
        mock_check_format.assert_called_once()
        mock_file.assert_called_once_with(shared.SETTINGS_FILE_PATH, 'w')

        # We test for json.dump since we upgraded to use the native function instead of write(json.dumps())
        mock_json_dump.assert_called_once_with(self.state.raw_settings, mock_file(), indent=4)
        mock_propagate.assert_called_once()

    @patch.object(core.AppConfig, 'check_paths')
    def test_save__invalid(self, mock_check_paths):
        mock_check_paths.return_value = False
        settings_to_save = {
            shared.Setting.LIBRARY: f"{TRIALS_PATH}/__test_lib",
        }
        self.assertRaises(shared.InternalError, self.state.save, settings_to_save)


if __name__ == '__main__':
    unittest.main()
