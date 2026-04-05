import unittest
from unittest.mock import patch, mock_open

from source.messaging import InternalError
from source.constants import MOD_DEF_FILE_NAME
import source.constructor as constructor


class Test_Constructor(unittest.TestCase):

    # --- 1. Test ConstructShared ---

    def test_construct_shared_add(self):
        shared_list = constructor.ConstructShared()
        dummy_level = constructor.ConstructLevel("TestClass")

        # When adding a level, it should be appended and marked as open
        result = shared_list.add(dummy_level)
        self.assertEqual(len(shared_list), 1)
        self.assertTrue(shared_list[-1].is_open)
        self.assertIs(result, shared_list[-1])

    def test_construct_shared_assign(self):
        shared_list = constructor.ConstructShared()

        # Test assigning to a new dictionary (index=None)
        shared_list.assign(index=None, name="Object1", value=10)
        self.assertEqual(len(shared_list), 1)
        self.assertEqual(shared_list[0], {"name": "Object1", "value": 10})

        # Test updating an existing dictionary
        shared_list.assign(index=0, type="Building")
        self.assertEqual(shared_list[0], {"name": "Object1", "value": 10, "type": "Building"})

        # Test assigning empty values (they should be filtered out)
        shared_list.assign(index=0, empty="")
        self.assertNotIn("empty", shared_list[0])

    def test_construct_shared_last(self):
        shared_list = constructor.ConstructShared()
        level_1 = constructor.ConstructLevel("Parent")
        level_2 = constructor.ConstructLevel("Child")

        # Add parent (opens it)
        shared_list.add(level_1)
        self.assertIs(shared_list.last(), level_1)

        # Add child to parent (opens child)
        level_1.add(level_2)
        self.assertIs(shared_list.last(), level_2)

        # Close child; the last open level should now be the parent again
        level_2.is_open = False
        self.assertIs(shared_list.last(), level_1)

    # --- 2. Test ConstructFile Structure Recognition ---

    @patch('source.constants.INI_DELIMITERS', [[["Object", "Weapon"], ["SubObject"]]])
    @patch('builtins.open', new_callable=mock_open, read_data="Object FakeUnit\n  SubObject fake_part\n")
    def test_recognize_structure__ini(self, mock_file):
        file_obj = constructor.ConstructFile("")  # Initialize empty to avoid auto-construction
        file_obj.name = "test.ini"

        file_obj.delimiters, file_obj.start_level = constructor.recognize_structure(file_obj.name)

        # It should have found the matching delimiter list and set start level to 0
        self.assertEqual(file_obj.start_level, 0)
        self.assertTrue(len(file_obj.delimiters) > 0)

    def test_recognize_structure__str(self):
        file_obj = constructor.ConstructFile("")
        file_obj.name = "test.str"

        # Mock the shared STR_DELIMITERS
        with patch('source.constants.STR_DELIMITERS', [["StringKey"]]):
            file_obj.delimiters, file_obj.start_level = constructor.recognize_structure(file_obj.name)

            # .str files hardcode start_level to 0 and append an empty list to delimiters
            self.assertEqual(file_obj.start_level, 0)
            self.assertEqual(file_obj.delimiters[-1], [])

    def test_recognize_structure__functional_file(self):
        file_obj = constructor.ConstructFile("")
        file_obj.name = MOD_DEF_FILE_NAME

        # It should raise an InternalError if trying to parse the mod definition file
        self.assertRaisesRegex(InternalError, "functional file", constructor.recognize_structure, file_obj.name)

    # --- 3. Test load_file Helper ---

    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('os.path.isfile')
    def test_load_directories__mode_0(self, mock_isfile, mock_isdir, mock_listdir):
        # Setup fake directory structure
        mock_listdir.return_value = ["folder1", "file1.txt", "file2.ini"]
        mock_isdir.side_effect = lambda path: "folder" in path
        mock_isfile.side_effect = lambda path: "file" in path

        folders, files = constructor.load_directories("C:/Fake/Dir", mode=0)

        # In mode 0, it should return ONLY the item names, not the full paths
        self.assertEqual(folders, ["folder1"])
        self.assertEqual(files, ["file1.txt", "file2.ini"])

    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('os.path.isfile')
    def test_load_directories__mode_1(self, mock_isfile, mock_isdir, mock_listdir):
        # Setup fake directory structure. We use side_effect to return different
        # contents depending on which directory os.listdir is asked to look inside.
        def listdir_mock(path):
            if path == "Root":
                return ["SubFolder", "root_file.txt"]
            elif path == "Root/SubFolder":
                return ["sub_file.ini"]
            return []

        mock_listdir.side_effect = listdir_mock

        # Explicitly match the exact paths to prevent false positives
        mock_isdir.side_effect = lambda path: path in ["Root", "Root/SubFolder"]
        mock_isfile.side_effect = lambda path: path in ["Root/root_file.txt", "Root/SubFolder/sub_file.ini"]

        folders, files = constructor.load_directories("Root", mode=1)

        # In mode 1, it should return full paths and recurse into subdirectories.
        self.assertEqual(folders, ["Root/SubFolder"])
        self.assertEqual(files, ["Root/SubFolder/sub_file.ini", "Root/root_file.txt"])


class Test_ConstructFile_Parser(unittest.TestCase):
    """ Tests the isolated syntax rules of the new ConstructFile delegation pattern. """

    def setUp(self):
        # We create a blank ConstructFile without a name so it doesn't auto-run construct()
        self.file = constructor.ConstructFile()
        self.file.name = "test.ini"

        # Manually set up the parser state that construct() would normally set
        self.file.delimiters = [["Object", "ChildObject"], ["Armor"]]
        self.file.current_level = 0
        self.file.last_comment = ""

        # We patch INI_ENDS so we don't depend on external constants
        self.patcher_ends = patch('source.constructor.INI_ENDS', ['End'])
        self.patcher_ends.start()

    def tearDown(self):
        self.patcher_ends.stop()

    # --- 1. Testing Syntax Helpers ---

    def test_extract_comments(self):
        """ Tests that code and comments are safely separated. """
        # Test semicolon comment
        words, signs = self.file._extract_comments("Health = 100 ; This is a comment")
        self.assertEqual(words, ["Health", "100"])
        self.assertEqual(signs, ["Health", "=", "100"])
        self.assertEqual(self.file.last_comment, "; This is a comment")

        # Test double slash comment with existing buffer
        words, signs = self.file._extract_comments("Armor // Another comment")
        self.assertEqual(words, ["Armor"])
        self.assertEqual(self.file.last_comment, "; This is a comment\n// Another comment")

    def test_handle_empty_line(self):
        """ Tests that empty lines bind floating comments to the tree. """
        self.file.last_comment = "; Floating note"
        self.file._handle_empty_line("   \n")

        # The comment should be added to the items list and the buffer cleared
        self.assertEqual(self.file.items[0], {'comment': '; Floating note'})
        self.assertEqual(self.file.last_comment, "")

    def test_handle_block_start(self):
        """ Tests that recognized keywords open a new ConstructLevel. """
        words = ["ChildObject", "GondorArcher_child", "GondorArcher"]

        # Execute
        result = self.file._handle_block_start(words)

        # Assertions
        self.assertTrue(result)
        self.assertEqual(self.file.current_level, 1)  # Level went up!
        self.assertIsInstance(self.file.items[0], constructor.ConstructLevel)
        self.assertEqual(self.file.items[0]._class, "ChildObject")
        # Ensure it extracted the name correctly for an INI file
        self.assertEqual(self.file.items[0].items[0],
                         {'class': 'ChildObject', 'name': 'GondorArcher_child', 'identifier': 'GondorArcher'})

    def test_handle_block_end(self):
        """ Tests that 'End' keywords correctly close the active block. """
        # Setup an active block first
        active_level = self.file.add(constructor.ConstructLevel(_class="Object"))
        self.file.current_level = 1

        # Add a trailing comment before closing
        self.file.last_comment = "; Ending soon"

        result = self.file._handle_block_end(["End"])

        self.assertTrue(result)
        self.assertEqual(self.file.current_level, 0)  # Level went down!
        self.assertFalse(active_level.is_open)  # The block is officially closed
        self.assertEqual(active_level.items[-2], {'comment': '; Ending soon'})
        self.assertEqual(active_level.items[-1], {'end': 'End'})

    def test_handle_directives(self):
        """ Tests #define and #include statements. """
        # Test #define
        result = self.file._handle_directives(["#define", "MACRO", "100"], ["#define", "MACRO", "100"])
        self.assertTrue(result)
        self.assertIn("#define MACRO 100", self.file.defines)

        # Test #include
        self.file.add(constructor.ConstructLevel(_class="Object"))  # We need an active level to attach the include to
        result = self.file._handle_directives(["#include", '"file.inc"'], ["#include", '"file.inc"'])
        self.assertTrue(result)
        self.assertEqual(self.file.last().items[1], {'include': '#include "file.inc"'})

    def test_handle_statement(self):
        """ Tests standard property assignment. """
        self.file.add(constructor.ConstructLevel(_class="Object"))
        self.file._handle_statement(["Health", "=", "100"])
        self.assertEqual(self.file.last().items[1], {'statement': 'Health = 100'})

    # --- 2. Testing the Main Router ---

    @patch('os.path.isfile', return_value=True)
    @patch('source.constructor.recognize_structure', return_value=([["Object"]], 0))
    @patch.object(constructor.ConstructFile, '_parse_line')
    def test_construct_router(self, mock_parse_line, mock_recognize, mock_isfile):
        """ Tests that the main loop successfully opens the file and routes every line. """
        fake_file_content = "Object GondorArcher\nHealth = 100\nEnd\n"

        with patch('builtins.open', mock_open(read_data=fake_file_content)):
            self.file.construct()

        # It should have called _parse_line exactly 3 times (once per line)
        self.assertEqual(mock_parse_line.call_count, 3)
        mock_parse_line.assert_any_call("Object GondorArcher\n")
        mock_parse_line.assert_any_call("Health = 100\n")
        mock_parse_line.assert_any_call("End\n")


class Test_LoadFile(unittest.TestCase):
    """ Tests the decoupled loading logic. """

    @patch('os.path.isfile', return_value=False)
    def test_load_file_invalid_path(self, mock_isfile):
        self.assertRaises(InternalError, constructor.load_file, "C:/fake.ini")

    @patch('os.path.isfile', return_value=True)
    @patch('source.constructor._load_structured_file')
    def test_load_file_routing(self, mock_load_structured, mock_isfile):
        # Should route .ini to the structured loader
        constructor.load_file("mod.ini")
        mock_load_structured.assert_called_once_with("mod.ini")

    @patch('source.constructor._load_raw_text', return_value=("RAW TEXT", []))
    @patch.object(constructor.ConstructFile, 'print', return_value="")
    @patch.object(constructor.ConstructFile, 'construct')  # Bypass actual parsing
    def test_load_structured_fallback(self, mock_construct, mock_print, mock_raw_text):
        """ Tests that an empty or failed parse correctly falls back to raw text. """
        # Because we patched print() to return "", the parser "failed" to generate output
        content, delimiters = constructor._load_structured_file("test.ini")

        # It should have fallen back to the raw loader
        mock_raw_text.assert_called_once_with("test.ini")
        self.assertEqual(content, "RAW TEXT")


if __name__ == '__main__':
    unittest.main()
