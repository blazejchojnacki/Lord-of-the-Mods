import unittest
from unittest.mock import patch, mock_open
import os

import source.constructor as constructor
import source.shared as s


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

    @patch('source.shared.INI_DELIMITERS', [[["Object", "Weapon"], ["SubObject"]]])
    @patch('builtins.open', new_callable=mock_open, read_data="Object FakeUnit\n  SubObject fake_part\n")
    def test_recognize_structure__ini(self, mock_file):
        file_obj = constructor.ConstructFile("")  # Initialize empty to avoid auto-construction
        file_obj.name = "test.ini"

        file_obj.recognize_structure()

        # It should have found the matching delimiter list and set start level to 0
        self.assertEqual(file_obj.start_level, 0)
        self.assertTrue(len(file_obj.delimiters) > 0)

    def test_recognize_structure__str(self):
        file_obj = constructor.ConstructFile("")
        file_obj.name = "test.str"

        # Mock the shared STR_DELIMITERS
        with patch('source.shared.STR_DELIMITERS', [["StringKey"]]):
            file_obj.recognize_structure()

            # .str files hardcode start_level to 0 and append an empty list to delimiters
            self.assertEqual(file_obj.start_level, 0)
            self.assertEqual(file_obj.delimiters[-1], [])

    def test_recognize_structure__functional_file(self):
        file_obj = constructor.ConstructFile("")
        file_obj.name = s.MOD_DEF_FILE_NAME

        # It should raise an InternalError if trying to parse the mod definition file
        self.assertRaisesRegex(s.InternalError, "functional file", file_obj.recognize_structure)

    # --- 3. Test load_file Helper ---

    @patch('os.path.isfile')
    def test_load_file__invalid_paths(self, mock_isfile):
        # Path does not exist
        mock_isfile.return_value = False
        self.assertRaisesRegex(s.InternalError, "wrong path", constructor.load_file, "fake.txt")

        # Empty path
        mock_isfile.return_value = True
        self.assertRaisesRegex(s.InternalError, "empty path", constructor.load_file, "")

        # Unsupported extension
        self.assertRaisesRegex(s.InternalError, "unsupported file type", constructor.load_file, "file.png")

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


if __name__ == '__main__':
    unittest.main()
