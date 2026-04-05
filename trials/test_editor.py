import unittest
from unittest.mock import patch, mock_open

from source.messaging import InternalError
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


class Test_Editor_Duplicates(unittest.TestCase):

    # --- 1. Testing spot_duplicates_in_file ---

    @patch('source.editor.extract_titles')
    def test_spot_duplicates_in_file_success(self, mock_extract):
        """ Tests that it accurately formats the string for local duplicates. """
        # We don't need mock_open anymore! We just mock the helper's output.
        mock_extract.return_value = {
            "Object UniqueUnit": ["1"],
            "Object DuplicatedUnit": ["4", "6"]
        }

        result = editor.spot_duplicates_in_file("test.ini")

        # It should completely ignore UniqueUnit, but flag DuplicatedUnit on lines 4 and 6
        self.assertIn("Object DuplicatedUnit -- line 4, 6;", result)
        self.assertNotIn("UniqueUnit", result)

    def test_spot_duplicates_in_file_invalid_extension(self):
        """ Tests that it safely rejects non-structured files. """
        with self.assertRaises(InternalError):
            editor.spot_duplicates_in_file("readme.txt")

    # --- 2. Testing extract_titles ---

    @patch('source.editor.constructor.recognize_structure')
    def test_extract_titles(self, mock_recognize):
        """ Tests that it successfully maps structural titles to lists of their line numbers. """
        mock_recognize.return_value = ([["Object", "Armor"]], 0)

        fake_content = (
            "; A comment line\n"  # Line 1
            "Object GondorArcher\n"  # Line 2
            "  Health = 100\n"  # Line 3
            "End\n"  # Line 4
            "Armor ArcherArmor\n"  # Line 5
        )

        with patch('builtins.open', mock_open(read_data=fake_content)):
            titles_dict = editor.extract_titles("test.ini")

        # It should correctly identify the blocks and map them to LISTS of strings
        self.assertEqual(len(titles_dict), 2)
        self.assertEqual(titles_dict["Object GondorArcher"], ["2"])
        self.assertEqual(titles_dict["Armor ArcherArmor"], ["5"])

    @patch('source.editor.constructor.recognize_structure')
    def test_extract_titles_functional_file(self, mock_recognize):
        """ Tests that it safely returns an empty dict if the file isn't supported. """
        mock_recognize.side_effect = InternalError("functional file")
        result = editor.extract_titles("mod_def.json")
        self.assertEqual(result, {})

    # --- 3. Testing spot_duplicates_from_file_in_file ---

    @patch('source.editor.extract_titles')
    def test_spot_duplicates_from_file_in_file(self, mock_extract):
        """ Tests that cross-file scanning correctly compares the two dictionaries. """
        def fake_extract(file_path):
            if file_path == "source.ini":
                return {"Object CrossUnit": ["15"], "Object SourceOnly": ["20"]}
            elif file_path == "target.ini":
                return {"Object CrossUnit": ["2"], "Object TargetOnly": ["5"]}
            return {}

        mock_extract.side_effect = fake_extract

        result = editor.spot_duplicates_from_file_in_file("source.ini", "target.ini")

        # The output should state where it was found in the target AND where it came from in the source
        self.assertIn("line 2 Object CrossUnit", result)
        self.assertIn("and in source, line 15;", result)

        # It should ignore items that don't overlap
        self.assertNotIn("SourceOnly", result)
        self.assertNotIn("TargetOnly", result)

    @patch('source.editor.spot_duplicates_in_file')
    def test_spot_duplicates_from_file_in_file_same_path(self, mock_spot_in_file):
        """ Tests that if you cross-scan a file against itself, it delegates to the single-file scanner. """
        mock_spot_in_file.return_value = "Delegated Result"

        result = editor.spot_duplicates_from_file_in_file("C:/same.ini", "C:/same.ini")

        self.assertEqual(result, "Delegated Result")
        mock_spot_in_file.assert_called_once_with("C:/same.ini")

    # --- 4. Testing spot_duplicates_in_directory ---

    @patch('os.walk')
    @patch('os.path.abspath')
    @patch('source.editor.spot_duplicates_from_file_in_file')
    def test_spot_duplicates_in_directory(self, mock_spot_from_file, mock_abspath, mock_walk):
        """ Tests the master directory looper. """

        # Simulate a directory tree with 3 files
        mock_walk.return_value = [
            ("C:/Fake/Dir", [], ["source.ini", "target1.ini", "target2.ini"])
        ]

        # Mock abspath to just return the path it was given (simplifies path matching logic for the test)
        mock_abspath.side_effect = lambda x: x

        # Pretend it finds a duplicate in target1, but not in target2
        def fake_scanner(source, target):
            if "target1.ini" in target:
                return "\tline 10 Object Found\n"
            return ""

        mock_spot_from_file.side_effect = fake_scanner

        # Execute
        result = editor.spot_duplicates_in_directory("C:/Fake/Dir/source.ini", "C:/Fake/Dir")

        # 1. It should NOT have scanned source.ini against itself because the loop skips abspath matches
        # 2. It SHOULD report the duplicate found in target1.ini
        self.assertIn("\tline 10 Object Found\n", result)

        # Verify it was only called exactly twice (for target1 and target2)
        self.assertEqual(mock_spot_from_file.call_count, 2)
        mock_spot_from_file.assert_any_call("C:/Fake/Dir/source.ini", "C:/Fake/Dir/target1.ini")
        mock_spot_from_file.assert_any_call("C:/Fake/Dir/source.ini", "C:/Fake/Dir/target2.ini")


if __name__ == '__main__':
    unittest.main()
