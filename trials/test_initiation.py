import unittest
from unittest.mock import patch

import interface.initiation as initiation


class Test_Initiation_UI(unittest.TestCase):

    # --- 1. Testing error termination ---

    @patch('interface.initiation.exit')
    @patch('interface.initiation.showerror')
    def test_cancel_initiation(self, mock_showerror, mock_exit):
        """ Tests that cancelling shows an error window and explicitly calls exit(). """
        initiation.cancel_initiation()

        # Verify the error popup was triggered
        mock_showerror.assert_called_once()
        # Verify the script was terminated
        mock_exit.assert_called_once()

    # --- 2. Testing Game Directory Prompts ---

    @patch('interface.initiation.search_reg')
    def test_get_game_directory_from_registry(self, mock_search_reg):
        """ Tests the flow when the game is found automatically in the Registry. """
        # Simulate finding the path automatically
        mock_search_reg.return_value = "C:\\Auto\\Game\\Path\\"

        result = initiation.get_game_directory()

        # It should replace backslashes automatically
        self.assertEqual(result[0], "C:/Auto/Game/Path/")
        # Ensure it processed every game in the game_list
        self.assertEqual(len(result), len(initiation.game_list))

    @patch('interface.initiation.askdirectory')
    @patch('interface.initiation.search_reg')
    def test_get_game_directory_from_prompt(self, mock_search_reg, mock_askdirectory):
        """ Tests the flow when registry fails and the user must pick a folder. """
        # Simulate registry failing (returns empty string)
        mock_search_reg.return_value = ""

        # Simulate the user choosing a path in the popup window
        mock_askdirectory.return_value = "D:/User/Selected/Game"

        result = initiation.get_game_directory()

        self.assertEqual(result[0], "D:/User/Selected/Game")
        mock_askdirectory.assert_called()

    @patch('interface.initiation.cancel_initiation')
    @patch('interface.initiation.askdirectory')
    @patch('interface.initiation.search_reg')
    def test_get_game_directory_cancelled(self, mock_search_reg, mock_askdirectory, mock_cancel):
        """ Tests that clicking 'Cancel' on the directory prompt terminates the setup. """
        mock_search_reg.return_value = ""
        # Simulate the user clicking "Cancel" in the Tkinter popup (returns empty string)
        mock_askdirectory.return_value = ""

        initiation.get_game_directory()

        # Verify our termination function was triggered
        mock_cancel.assert_called()

    # --- 3. Testing Library/Archive Directory Prompts ---

    @patch('interface.initiation.invoke_choice')
    def test_get_directories_default(self, mock_invoke):
        """ Tests the user clicking 'Use default' for functional folders. """
        # Simulate clicking "Use default" (returns True)
        mock_invoke.return_value = True

        result = initiation.get_directories()

        # It should just pass back the default folders dict!
        self.assertEqual(result, initiation.default_folders_dict)

    @patch('os.path.isdir', return_value=True)
    @patch('interface.initiation.askdirectory')
    @patch('interface.initiation.invoke_choice')
    def test_get_directories_custom(self, mock_invoke, mock_askdirectory, mock_isdir):
        """ Tests the user clicking 'Choose own' and picking valid folders. """
        # Simulate clicking "Choose own" (returns False)
        mock_invoke.return_value = False

        # Simulate the user selecting a valid directory
        mock_askdirectory.return_value = "E:/Custom/Folder"

        result = initiation.get_directories()

        # Both library and archive should be set to the user's choices
        self.assertEqual(result['library'], "E:/Custom/Folder")
        self.assertEqual(result['archive'], "E:/Custom/Folder")

    # --- 4. Testing the Main UI Orchestrator ---

    @patch('interface.initiation.execute_initiation')
    @patch('interface.initiation.get_directories')
    @patch('interface.initiation.get_game_directory')
    @patch('os.path.isfile')
    @patch('tkinter.Toplevel')
    @patch('tkinter.Label')
    @patch('tkinter.Tk')
    def test_initiate_first_time(self, mock_tk, mock_label, mock_toplevel, mock_isfile,
                                 mock_get_game, mock_get_dirs, mock_execute):
        """ Tests the main window startup when settings do not exist. """
        # Simulate SETTINGS_FILE_PATH not existing
        mock_isfile.return_value = False

        # Provide dummy data from our mocked UI prompts
        mock_get_game.return_value = ["C:/Game1"]
        mock_get_dirs.return_value = {"library": "lib", "archive": "arch"}

        # Execute the window!
        initiation.initiate()

        # Verify the UI successfully gathered the data and handed it to the logic layer
        mock_execute.assert_called_once_with(["C:/Game1"], {"library": "lib", "archive": "arch"})

        # Verify the window was closed at the end
        mock_tk.return_value.destroy.assert_called_once()


if __name__ == '__main__':
    unittest.main()
