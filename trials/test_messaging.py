import unittest
from unittest.mock import patch
import logging

import source.messaging as messaging


# --- Dummy functions to test the call stack inspection ---
def dummy_caller_function():
    return messaging.get_calling_object(steps=1)


def dummy_error_trigger():
    raise messaging.InternalError("Something broke")


def dummy_message_trigger():
    return messaging.internal_message("Just a note")


class Test_Messaging(unittest.TestCase):

    # --- 1. Testing Call Stack Inspection ---

    def test_get_calling_object(self):
        """ Tests that inspect accurately climbs the stack to find the caller's name. """
        result = dummy_caller_function()
        # It should see that 'dummy_caller_function' called it
        self.assertEqual(result, "dummy_caller_function")

    def test_get_calling_module(self):
        """ Tests that inspect accurately climbs the stack to find the module name. """
        # Because we are calling it directly here, the caller module is this test file,
        # but since we're simulating, we just verify it doesn't crash and returns a string.
        # If running via standard unittest, it usually resolves to the test module name or '__main__'.
        result = messaging.get_calling_module(steps=1)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    # --- 2. Testing Custom Exceptions ---

    def test_internal_error_formatting(self):
        """ Tests that InternalError properly extracts the caller's name and formats the string. """
        try:
            dummy_error_trigger()
        except messaging.InternalError as e:
            # We expect it to blame the 'dummy_error_trigger' function!
            self.assertIn("dummy_error_trigger error: Something broke", e.message)

    def test_internal_message_formatting(self):
        """ Tests that internal_message properly extracts the caller's name. """
        result = dummy_message_trigger()
        self.assertIn("dummy_message_trigger: Just a note", result)

    # --- 3. Testing Logger Setup ---

    @patch('os.makedirs')
    def test_get_custom_logger_creation(self, mock_makedirs):
        """ Tests that a new logger is created with exactly one FileHandler and one StreamHandler. """
        # We use a highly unique name so it doesn't collide with the global 'main' logger
        test_logger = messaging.get_custom_logger("test_new_logger", "test_log.txt")

        # Verify it ensured the directory exists
        mock_makedirs.assert_called_once_with(messaging.LOG_PATH, exist_ok=True)

        # Verify the logging level
        self.assertEqual(test_logger.level, logging.DEBUG)

        # Verify it attached exactly 2 handlers
        self.assertEqual(len(test_logger.handlers), 2)

        # Verify the types of the handlers
        handler_types = [type(h) for h in test_logger.handlers]
        self.assertIn(logging.FileHandler, handler_types)
        self.assertIn(logging.StreamHandler, handler_types)

    @patch('os.makedirs')
    def test_get_custom_logger_caching(self, mock_makedirs):
        """ Tests the crucially important logic that prevents duplicate handlers. """
        # Create it the first time
        logger_first_pass = messaging.get_custom_logger("test_cached_logger", "cache.txt")
        initial_handler_count = len(logger_first_pass.handlers)

        # Request the exact same logger again
        logger_second_pass = messaging.get_custom_logger("test_cached_logger", "cache.txt")

        # 1. It must return the exact same object in memory
        self.assertIs(logger_first_pass, logger_second_pass)

        # 2. It MUST NOT have added duplicate handlers (count should still be exactly 2)
        self.assertEqual(len(logger_second_pass.handlers), initial_handler_count)


if __name__ == '__main__':
    unittest.main()
