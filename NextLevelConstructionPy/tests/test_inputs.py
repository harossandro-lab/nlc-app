"""Number input and display helpers (no Qt)."""
import unittest

from nlc.formatting import number_text
from nlc.inputs import parse_number, parse_whole_number


class ParseNumberTests(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(parse_number("8.25"), 8.25)
        self.assertEqual(parse_number(" 10 "), 10.0)
        self.assertEqual(parse_number("-4"), -4.0)
        self.assertEqual(parse_number("1e2"), 100.0)

    def test_blank_means_zero_like_the_web(self):
        self.assertEqual(parse_number(""), 0.0)
        self.assertEqual(parse_number("   "), 0.0)
        self.assertEqual(parse_number(None), 0.0)

    def test_text_is_rejected(self):
        for text in ("abc", "12abc", "1,5", "NaN", "Infinity", "1_0", "$5"):
            self.assertIsNone(parse_number(text), text)

    def test_whole_number(self):
        self.assertEqual(parse_whole_number("3"), 3)
        self.assertEqual(parse_whole_number("3.7"), 3)
        self.assertEqual(parse_whole_number(""), 0)
        self.assertIsNone(parse_whole_number("x"))


class NumberTextTests(unittest.TestCase):
    def test_number_text(self):
        self.assertEqual(number_text(8.25), "8.25")
        self.assertEqual(number_text(3.0), "3")
        self.assertEqual(number_text(0), "0")
        self.assertEqual(number_text(0.0), "0")
        self.assertEqual(number_text(None), "")
        self.assertEqual(number_text(10.5), "10.5")


if __name__ == "__main__":
    unittest.main()
