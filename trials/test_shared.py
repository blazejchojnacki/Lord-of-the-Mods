import unittest
from unittest.mock import patch, mock_open, MagicMock
import json

import source.shared as shared


class Test_Shared(unittest.TestCase):

    # --- 1. MOCKED: Logging Logic ---

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('os.mkdir')
    @patch('builtins.open', new_callable=mock_open)
    def test_log__creates_dir_and_writes(self, mock_file, mock_mkdir, mock_isfile, mock_isdir):
        # Pretend the log directory does NOT exist initially, but exists after creation
        mock_isfile.side_effect = lambda path: False
        mock_isdir.side_effect = lambda path: path == shared.LOG_PATH

        shared.log("test message", "test.txt")

        # Verify directory was created and file was opened in 'w' (write) mode
        mock_mkdir.assert_called_once_with(shared.LOG_PATH)
        mock_file.assert_called_once_with(f'{shared.LOG_PATH}/test.txt', 'w')
        mock_file().write.assert_called_once_with("test message\n")

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('builtins.open', new_callable=mock_open)
    def test_log__appends_to_existing_file(self, mock_file, mock_isfile, mock_isdir):
        # Pretend the log directory AND the target file already exist
        mock_isfile.side_effect = lambda path: path == f'{shared.LOG_PATH}/test.txt'
        mock_isdir.return_value = True

        with patch('os.mkdir') as mock_mkdir:
            shared.log("test append", "test.txt")

            # Verify directory creation was skipped and file was opened in 'a' (append) mode
            mock_mkdir.assert_not_called()
            mock_file.assert_called_once_with(f'{shared.LOG_PATH}/test.txt', 'a')
            mock_file().write.assert_called_once_with("test append\n")

    # --- 2. DIRECT: Inspection and Exceptions ---

    def test_get_calling_module_and_object(self):
        # We wrap the calls in a dummy function to simulate a nested call stack
        def dummy_caller():
            # Steps=1 looks directly at the function that called get_calling_*
            mod = shared.get_calling_module(steps=1)
            obj = shared.get_calling_object(steps=1)
            return mod, obj

        mod_name, obj_name = dummy_caller()

        # It should correctly identify this test file and the dummy function
        self.assertTrue("test_shared" in mod_name)
        self.assertEqual(obj_name, "Test_Shared.test_get_calling_module_and_object.<locals>.dummy_caller")

    def test_internal_error_formatting(self):
        def dummy_error_raiser():
            raise shared.InternalError("test failure")

        with self.assertRaises(shared.InternalError) as context:
            dummy_error_raiser()

        # The exception message should automatically prepend the caller's module and name
        self.assertIn("dummy_error_raiser", context.exception.message)
        self.assertIn("error: test failure", context.exception.message)

    # --- 3. MOCKED: Global Variable Loading ---

    @patch('source.shared.windll', create=True)  # Mock windll to prevent Windows API crashes
    @patch('tkinter.PhotoImage')  # Mock Tkinter images to avoid requiring a Tk instance
    @patch('os.path.isfile')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_aesthetic(self, mock_json_load, mock_file, mock_isfile, mock_photo, mock_windll):
        # Pretend the aesthetic config file exists
        mock_isfile.return_value = True

        # Provide dummy data for json.load to return
        mock_json_load.return_value = {
            "APP_BACKGROUND_COLOR": "#111111",
            "ENTRY_BACKGROUND_COLOR": "#222222",
            "TEXT_COLORS": ["#333333"],
            "INI_LEVEL_COLORS": ["#444444"],
            "FONT_FILE_NAME": "dummy.ttf",
            "FONT_NAME": "DummyFont",
            "FONT_SIZE_TEXT": 12,
            "FONT_SIZE_BUTTON": 14,
            "FONT_TYPE": "bold"
        }

        # Pretend the font was successfully loaded by Windows API
        mock_windll.gdi32.AddFontResourceExW.return_value = 1

        # Call the function
        shared.load_aesthetic()

        # Verify globals were updated
        self.assertEqual(shared.APP_BACKGROUND_COLOR, "#111111")
        self.assertEqual(shared.ENTRY_BACKGROUND_COLOR, "#222222")
        self.assertEqual(shared.TEXT_COLORS, ["#333333"])
        self.assertEqual(shared.FONT_TEXT, ("DummyFont", 12, "bold"))
        self.assertEqual(shared.FONT_BUTTON, ("DummyFont", 14, "bold"))


if __name__ == '__main__':
    unittest.main()