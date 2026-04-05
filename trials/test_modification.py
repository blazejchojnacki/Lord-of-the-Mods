import unittest
from unittest.mock import patch

from source.messaging import InternalError
import interface.modification as modification


class Test_Modification_UI(unittest.TestCase):

    # --- 1. Testing get_available_name_ui ---

    @patch('interface.modification.get_available_name')
    def test_get_available_name_ui_success(self, mock_get_name):
        """ Tests that it bypasses the UI if the logic layer successfully finds a name. """
        mock_get_name.return_value = "snapshots/snap1.json"

        result = modification.get_available_name_ui("snapshots")

        self.assertEqual(result, "snapshots/snap1.json")
        mock_get_name.assert_called_once_with("snapshots", "snapshot")

    @patch('interface.modification.askstring')
    @patch('interface.modification.get_available_name')
    def test_get_available_name_ui_fallback(self, mock_get_name, mock_askstring):
        """ Tests that it prompts the user if the auto-namer fails. """
        mock_get_name.side_effect = InternalError("Index error")
        mock_askstring.return_value = "custom_name"

        result = modification.get_available_name_ui("snapshots")

        self.assertEqual(result, "snapshots/snapshotcustom_name.json")
        mock_askstring.assert_called_once()

    @patch('interface.modification.askstring')
    @patch('interface.modification.get_available_name')
    def test_get_available_name_ui_cancelled(self, mock_get_name, mock_askstring):
        """ Tests that cancelling the string prompt safely raises an error. """
        mock_get_name.side_effect = InternalError("Index error")
        mock_askstring.return_value = ""  # User clicked Cancel

        with self.assertRaises(InternalError):
            modification.get_available_name_ui("snapshots")

    # --- 2. Testing snapshot_take_ui ---

    @patch('interface.modification.snapshot_take')
    def test_snapshot_take_ui_preprovided(self, mock_take):
        """ Tests that passing paths directly bypasses the UI completely. """
        modification.snapshot_take_ui(game_paths=["C:/Game1"])
        mock_take.assert_called_once_with(["C:/Game1"])

    @patch('interface.modification.snapshot_take')
    @patch('interface.modification.askdirectory')
    def test_snapshot_take_ui_loop(self, mock_askdir, mock_take):
        """ Tests that it loops gathering directories until the user clicks cancel. """
        # Simulate user picking two directories, then clicking cancel (empty string)
        mock_askdir.side_effect = ["C:/Game1", "C:/Game2", ""]

        modification.snapshot_take_ui()

        self.assertEqual(mock_askdir.call_count, 3)
        mock_take.assert_called_once_with(["C:/Game1", "C:/Game2"])

    @patch('interface.modification.askdirectory')
    def test_snapshot_take_ui_empty(self, mock_askdir):
        """ Tests that cancelling on the very first prompt aborts the snapshot. """
        mock_askdir.return_value = ""

        with self.assertRaises(InternalError):
            modification.snapshot_take_ui()

    # --- 3. Testing snapshot_compare_ui ---

    @patch('interface.modification.snapshot_compare')
    @patch('interface.modification.askopenfilename')
    def test_snapshot_compare_ui_prompts(self, mock_askfile, mock_compare):
        """ Tests that missing arguments trigger file dialogs in the correct order. """
        mock_askfile.side_effect = ["snap1.json", "snap2.json"]

        modification.snapshot_compare_ui(return_type='dict')

        self.assertEqual(mock_askfile.call_count, 2)
        mock_compare.assert_called_once_with("snap1.json", "snap2.json", 'dict')

    # --- 4. Testing initiate_comparison_ui ---

    @patch('interface.modification.initiate_comparison')
    @patch('interface.modification.askopenfilenames')
    @patch('interface.modification.askdirectory')
    def test_initiate_comparison_ui_directory(self, mock_askdir, mock_askfiles, mock_initiate):
        """ Tests the UI routing for 'directory' changes source. """
        mock_askdir.return_value = "C:/BaseGame"
        mock_askfiles.return_value = ["remove1.ini", "remove2.ini"]

        modification.initiate_comparison_ui("C:/MyMod", changes_source='directory')

        mock_askdir.assert_called_once()
        mock_askfiles.assert_called_once()
        mock_initiate.assert_called_once_with(
            "C:/MyMod", "C:/BaseGame", 'directory', ["remove1.ini", "remove2.ini"], None, None
        )

    @patch('interface.modification.initiate_comparison')
    @patch('interface.modification.askopenfilename')
    def test_initiate_comparison_ui_comparison(self, mock_askfile, mock_initiate):
        """ Tests the UI routing for 'comparison' changes source. """
        mock_askfile.return_value = "my_comparison.json"

        modification.initiate_comparison_ui("C:/MyMod", changes_source='comparison')

        mock_askfile.assert_called_once()
        mock_initiate.assert_called_once_with(
            "C:/MyMod", '', 'comparison', None, "my_comparison.json", None
        )

    @patch('interface.modification.initiate_comparison')
    @patch('interface.modification.askopenfilename')
    def test_initiate_comparison_ui_snapshot(self, mock_askfile, mock_initiate):
        """ Tests the UI routing for 'snapshot' changes source. """
        mock_askfile.return_value = "my_snapshot.json"

        modification.initiate_comparison_ui("C:/MyMod", changes_source='snapshot')

        mock_askfile.assert_called_once()
        mock_initiate.assert_called_once_with(
            "C:/MyMod", '', 'snapshot', None, None, "my_snapshot.json"
        )


if __name__ == '__main__':
    unittest.main()
