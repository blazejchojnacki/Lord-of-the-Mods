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

    @patch('os.path.isfile')
    def test_load_file__invalid_paths(self, mock_isfile):
        # Path does not exist
        mock_isfile.return_value = False
        self.assertRaisesRegex(InternalError, "wrong path", constructor.load_file, "fake.txt")

        # Empty path
        mock_isfile.return_value = True
        self.assertRaisesRegex(InternalError, "empty path", constructor.load_file, "")

        # Unsupported extension
        self.assertRaisesRegex(InternalError, "unsupported file type", constructor.load_file, "file.png")

    @patch('os.path.isfile')
    @patch('builtins.open', new_callable=mock_open, read_data="Just some text")
    def test_load_file__txt(self, mock_file, mock_isfile):
        mock_isfile.return_value = True

        content, levels = constructor.load_file("test.txt")

        # .txt files should just return raw content and empty levels
        self.assertEqual(content, "Just some text")
        self.assertEqual(levels, [])

    # --- 4. Test load_directories Helper ---

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


class Test_ConstructFile_Construct(unittest.TestCase):

    # --- 1. Test Invalid Files ---

    @patch('source.constructor.os.path.isfile')
    @patch.object(constructor.ConstructFile, 'recognize_structure')
    def test_construct__invalid_file(self, mock_recognize, mock_isfile):
        # Pretend the file doesn't exist
        mock_isfile.return_value = False

        # Initialize with an empty string to bypass the auto-construct in __init__
        file_obj = constructor.ConstructFile("")
        file_obj.name = "test.ini"

        # It should raise an InternalError because the file either doesn't exist
        # or doesn't have a valid extension
        self.assertRaisesRegex(InternalError, "invalid", file_obj.construct)

    # --- 2. Test Macros and Includes ---

    @patch('source.constructor.os.path.isfile')
    @patch.object(constructor.ConstructFile, 'recognize_structure')
    @patch('builtins.open', new_callable=mock_open, read_data="#define MY_MACRO 100\n#include \"file.inc\"\n")
    def test_construct__defines_and_includes(self, mock_file, mock_recognize, mock_isfile):
        mock_isfile.return_value = True

        file_obj = constructor.ConstructFile("")
        file_obj.name = "test.ini"
        file_obj.start_level = 0
        file_obj.delimiters = [[]]

        file_obj.construct()

        # It should extract the #define into the dedicated defines list
        self.assertEqual(file_obj.defines, ["#define MY_MACRO 100"])

        # It should extract the #include as an assigned dictionary on the root object
        self.assertEqual(file_obj[0], {"include": "#include \"file.inc\""})

    # --- 3. Test Blocks and Statements ---

    @patch('source.constructor.os.path.isfile')
    @patch.object(constructor.ConstructFile, 'recognize_structure')
    @patch('builtins.open', new_callable=mock_open, read_data="Object FakeUnit\n  Health = 100\nEnd\n")
    def test_construct__blocks_and_statements(self, mock_file, mock_recognize, mock_isfile):
        mock_isfile.return_value = True

        file_obj = constructor.ConstructFile("")
        file_obj.name = "test.ini"
        file_obj.start_level = 0
        # Tell the parser to treat "Object" as a block delimiter
        file_obj.delimiters = [["Object"], []]

        file_obj.construct()

        # The parser should have created exactly 1 ConstructLevel inside the main file
        self.assertEqual(len(file_obj), 1)
        level = file_obj[0]
        self.assertIsInstance(level, constructor.ConstructLevel)

        # Index 0 holds the block declaration (updated by level.assign)
        self.assertEqual(level[0], {"class": "Object", "name": "FakeUnit"})

        # Index 1 holds the parsed statement
        self.assertEqual(level[1], {"statement": "Health = 100"})

        # Index 2 holds the end of the block
        self.assertEqual(level[2], {"end": "End"})

    # --- 4. Test Comments (The tricky part!) ---

    @patch('source.constructor.os.path.isfile')
    @patch.object(constructor.ConstructFile, 'recognize_structure')
    @patch('builtins.open', new_callable=mock_open,
           read_data="; Main Comment\n\nObject FakeUnit // inline comment\nEnd\n")
    def test_construct__comments(self, mock_file, mock_recognize, mock_isfile):
        mock_isfile.return_value = True

        file_obj = constructor.ConstructFile("")
        file_obj.name = "test.ini"
        file_obj.start_level = 0
        file_obj.delimiters = [["Object"], []]

        file_obj.construct()

        # 1. The first comment precedes an empty line, so it should be appended to the root file object
        self.assertEqual(file_obj[0], {"comment": "; Main Comment"})

        # 2. The block should have been created with the inline comment attached to its declaration
        level = file_obj[1]
        self.assertIsInstance(level, constructor.ConstructLevel)
        self.assertEqual(level[0], {"class": "Object", "name": "FakeUnit", "comment": "// inline comment"})


if __name__ == '__main__':
    unittest.main()
