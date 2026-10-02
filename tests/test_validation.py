import unittest
from cryptolab.validation import *


class ValidationTests(unittest.TestCase):
    def test_boolean_integer(self):
        with self.assertRaises(ValueError):
            integer(True)

    def test_nonfinite_decimal(self):
        for v in ("NaN", "Infinity", "-Infinity"):
            with self.assertRaises(ValueError):
                decimal(v)

    def test_identity(self):
        for v in ("", " ", "a" * 201, None):
            with self.assertRaises(ValueError):
                identifier(v)

    def test_event_order(self):
        with self.assertRaises(ValueError):
            chronological([{"timestamp": 2}, {"timestamp": 1}])
