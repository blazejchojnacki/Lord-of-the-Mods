import unittest
from unittest.mock import patch, mock_open

import source.editor as editor


class Test_Editor(unittest.TestCase):

    def setUp(self):
        # Globally mock the log function for all tests in this class to prevent actual file writes
        self.patcher_log = patch('source.messaging.log')
        self.mock_log = self.patcher_log.start()

    def tearDown(self):
        self.patcher_log.stop()

    # --- 1. Test String Formatting ---

    def test_reformat_string(self):
        # Test "display" direction (converting actual newlines to the string "\n")
        raw_string = "Line 1\nLine 2\tTabbed"
        display_result = editor.reformat_string(raw_string, direction='display')
        self.assertEqual(display_result, r"Line·1\nLine·2\tTabbed")

        # Test "process" direction (converting string "\n" back to actual newlines)
        escaped_string = r"Line·1\nLine·2\tTabbed"
        process_result = editor.reformat_string(escaped_string, direction='process')
        self.assertEqual(process_result, "Line 1\nLine 2\tTabbed")

    # --- 2. Test Find and Replace ---

    @patch('os.path.isfile')
    @patch('builtins.open', new_callable=mock_open, read_data="Object GondorArcher\n  Health = 100\nEnd")
    def test_text_find_replace__find_only(self, mock_file, mock_isfile):
        mock_isfile.return_value = True

        # Finding a string without replacing it
        result = editor.text_find_replace(find="Health = 100", scope="test.ini")

        # It should read the file but NOT write to it
        mock_file.assert_called_once_with("test.ini")
        mock_file().write.assert_not_called()
        self.assertIn("found 1", result)

    @patch('os.path.isfile')
    @patch('builtins.open', new_callable=mock_open, read_data="Object GondorArcher\n  Health = 100\nEnd")
    def test_text_find_replace__replace(self, mock_file, mock_isfile):
        mock_isfile.return_value = True

        # Finding and replacing
        editor.text_find_replace(find="Health = 100", replace_with="Health = 200", scope="test.ini")

        # It should open the file for reading, then open it again for writing ('w')
        mock_file.assert_any_call("test.ini")
        mock_file.assert_any_call("test.ini", 'w')

        # Verify the content written back contains the replacement
        written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
        self.assertIn("Health = 200", written_content)
        self.assertNotIn("Health = 100", written_content)

    # --- 3. Test File Moving and Link Updates ---

    @patch('source.editor.update_links_to_inc')
    @patch('source.editor.shutil.move')
    def test_move_file__inc_file(self, mock_move, mock_update_inc):
        # Move a .inc file
        editor.move_file("C:/old_path/macros.inc", "C:/new_path/data/ini/includes")

        # Verify shutil.move was called correctly
        mock_move.assert_called_once_with("C:/old_path/macros.inc", "C:/new_path/data/ini/includes/macros.inc")

        # Verify it triggered the specific .inc link updater
        mock_update_inc.assert_called_once()

    @patch('source.editor.update_links_in_ini')
    @patch('source.editor.shutil.move')
    def test_move_file__ini_file(self, mock_move, mock_update_ini):
        # Move a .ini file
        editor.move_file("C:/old_path/unit.ini", "C:/new_path/objects")

        mock_move.assert_called_once_with("C:/old_path/unit.ini", "C:/new_path/objects/unit.ini")

        # Verify it triggered the specific .ini link updater
        mock_update_ini.assert_called_once()

    # --- 4. Test Duplicates Finder ---

    # # # missing tests for spot_duplicates


if __name__ == '__main__':
    unittest.main()
