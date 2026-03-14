import os.path
import unittest

import source.core as core
import source.shared


class Test_Settings(unittest.TestCase):
    def setUp(self):
        pass

    def test_create_directories(self):
        settings_to_initiate = {
            source.shared.Setting.LIBRARY: "trials/__test_lib",
            source.shared.Setting.ARCHIVE: "trials/__test_arch",
            source.shared.Setting.GAMES: ["trials/__test_game1", "./trials/__test_game2"],
            source.shared.Setting.EXCEPTIONS: ["trials/__test_not_mod1"],
        }
        core.settings.create_directories(settings_to_initiate)
        for key in settings_to_initiate:
            paths = []
            if isinstance(settings_to_initiate[key], str):
                paths = [settings_to_initiate[key]]
            elif isinstance(settings_to_initiate[key], list):
                paths = settings_to_initiate[key]
            for path in paths:
                self.assertTrue(os.path.isdir(path))
                os.rmdir(path)

    def test_propagate(self):
        value_copy = core.settings[source.shared.Setting.LIBRARY]
        core.settings[source.shared.Setting.LIBRARY] = "trials/__test_lib"
        core.settings.propagate()
        self.assertEqual(core.library, "trials/__test_lib")
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
            source.shared.Setting.LIBRARY: "trials",
        }
        self.assertTrue(core.settings.check_paths(settings_to_check))

    def test_check_paths__not_existing(self):
        settings_to_check = {
            source.shared.Setting.LIBRARY: "trials/__test_lib",
            source.shared.Setting.ARCHIVE: "trials/__test_arch",
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
                source.shared.Setting.LIBRARY: "trials/__test_lib",
            }
            for key in settings_to_save:
                paths = []
                if isinstance(settings_to_save[key], str):
                    paths = [settings_to_save[key]]
                elif isinstance(settings_to_save[key], list):
                    paths = settings_to_save[key]
                for path in paths:
                    os.makedirs(path, exist_ok=True)

            core.settings.save(settings_to_save)
            self.assertTrue(os.path.isfile(source.shared.SETTINGS_FILE_PATH))
            self.assertEqual(core.library, settings_to_save[source.shared.Setting.LIBRARY])

            for key in settings_to_save:
                paths = []
                if isinstance(settings_to_save[key], str):
                    paths = [settings_to_save[key]]
                elif isinstance(settings_to_save[key], list):
                    paths = settings_to_save[key]
                for path in paths:
                    os.rmdir(path)
        else:
            print(source.shared.internal_message('test not applicable'))

    def test_save__invalid(self):
        settings_to_save = {
            source.shared.Setting.LIBRARY: "trials/__test_lib",
        }
        self.assertRaises(source.shared.InternalError, core.settings.save, settings_to_save)
