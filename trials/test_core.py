import os.path
import unittest
from pathlib import Path

import source.core as core
import source.shared

TRIALS_PATH = "/".join(str(Path(__file__).parent).split('\\')[-2:])


class Test_Settings(unittest.TestCase):
    def setUp(self):
        pass

    def test_create_directories(self):
        settings_to_initiate = {
            source.shared.Setting.LIBRARY: f"{TRIALS_PATH}/__test_lib",
            source.shared.Setting.ARCHIVE: f"{TRIALS_PATH}/__test_arch",
            source.shared.Setting.GAMES: [f"{TRIALS_PATH}/__test_game1",
                                          f"{TRIALS_PATH}/__test_game2"],
            source.shared.Setting.EXCEPTIONS: [f"{TRIALS_PATH}/__test_lib/__test_not_mod1"],
        }
        core.settings.create_directories(settings_to_initiate)
        paths = core.complete_paths(settings_to_initiate)
        for path in paths:
            self.assertTrue(os.path.isdir(path))
        for path_index in range(len(paths), 0, -1):
            os.rmdir(paths[path_index-1])

    def test_propagate(self):
        value_copy = core.settings[source.shared.Setting.LIBRARY]
        propagated_path = f"{TRIALS_PATH}/__test_lib"
        core.settings[source.shared.Setting.LIBRARY] = propagated_path
        core.settings.propagate()
        self.assertEqual(core.library, f"{core.install_path}/{propagated_path}")
        core.settings[source.shared.Setting.LIBRARY] = value_copy
        core.settings.propagate()

    def test_load(self):
        # # # loading before the file is created
        if not os.path.isfile(source.shared.SETTINGS_FILE_PATH):
            self.assertDictEqual(core.settings, source.shared._SETTINGS_FORMAT)
            self.assertFalse(core.loaded)
        # # # loading from file
        else:
            for key in source.shared._SETTINGS_FORMAT:
                self.assertIn(key, core.settings)
            self.assertTrue(core.loaded)

    def test_check_format(self):
        core.settings['test_key'] = 'test_value'
        self.assertRaises(source.shared.InternalError, core.settings.check_format)
        value_copy = core.settings.pop(source.shared.Setting.LIBRARY)
        self.assertRaises(source.shared.InternalError, core.settings.check_format)
        core.settings.pop('test_key')
        core.settings[source.shared.Setting.LIBRARY] = value_copy

    def test_check_paths__existing(self):
        settings_to_check = {
            source.shared.Setting.LIBRARY: f"{TRIALS_PATH}",
        }
        self.assertTrue(core.settings.check_paths(settings_to_check))

    def test_check_paths__not_existing(self):
        settings_to_check = {
            source.shared.Setting.LIBRARY: f"{TRIALS_PATH}/__test_lib",
            source.shared.Setting.ARCHIVE: f"{TRIALS_PATH}/__test_arch",
        }
        self.assertFalse(core.settings.check_paths(settings_to_check))

    def test_check_paths__missing(self):
        settings_to_check = {
            source.shared.Setting.LIBRARY: "",
        }
        self.assertFalse(core.settings.check_paths(settings_to_check))

    def test_save__valid_new(self):
        if not os.path.isfile(source.shared.SETTINGS_FILE_PATH):
            settings_to_save = {
                source.shared.Setting.LIBRARY: f"{TRIALS_PATH}/__test_lib",
            }
            for path in core.complete_paths(settings_to_save):
                os.makedirs(path, exist_ok=True)

            core.settings.save(settings_to_save)
            self.assertTrue(os.path.isfile(source.shared.SETTINGS_FILE_PATH))
            self.assertEqual(core.library, settings_to_save[source.shared.Setting.LIBRARY])

            for path in core.complete_paths(settings_to_save):
                os.rmdir(path)
        else:
            settings_to_save = {
                source.shared.Setting.EXCEPTIONS: [f"{TRIALS_PATH}/__test_lib/test_exception"]
            }
            completed_paths = core.complete_paths(settings_to_save)
            for path in completed_paths:
                os.makedirs(path, exist_ok=True)

            core.settings.save(settings_to_save)
            self.assertEqual([f"{core.install_path}/{_}" for _ in settings_to_save[source.shared.Setting.EXCEPTIONS]],
                             core.exceptions)

            for path in completed_paths:
                os.rmdir(path)

    def test_save__invalid(self):
        settings_to_save = {
            source.shared.Setting.LIBRARY: f"{TRIALS_PATH}/__test_lib",
        }
        self.assertRaises(source.shared.InternalError, core.settings.save, settings_to_save)
