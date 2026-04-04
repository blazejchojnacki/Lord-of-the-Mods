import source.messaging as exceptions


def test_get_calling_module_and_object(self):
    # We wrap the calls in a dummy function to simulate a nested call stack
    def dummy_caller():
        # Steps=1 looks directly at the function that called get_calling_*
        mod = exceptions.get_calling_module(steps=1)
        obj = exceptions.get_calling_object(steps=1)
        return mod, obj

    mod_name, obj_name = dummy_caller()

    # It should correctly identify this test file and the dummy function
    self.assertTrue("test_shared" in mod_name)
    self.assertEqual(obj_name, "Test_Shared.test_get_calling_module_and_object.<locals>.dummy_caller")


def test_internal_error_formatting(self):
    def dummy_error_raiser():
        raise exceptions.InternalError("test failure")

    with self.assertRaises(exceptions.InternalError) as context:
        dummy_error_raiser()

    # The exception message should automatically prepend the caller's module and name
    self.assertIn("dummy_error_raiser", context.exception.message)
    self.assertIn("error: test failure", context.exception.message)
