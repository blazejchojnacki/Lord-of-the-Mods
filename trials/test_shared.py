import unittest
from unittest.mock import patch, mock_open

import source.shared as shared


class Test_Shared(unittest.TestCase):

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
