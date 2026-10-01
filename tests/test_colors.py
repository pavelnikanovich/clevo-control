# SPDX-License-Identifier: GPL-2.0-or-later
import unittest

from clevo_control import colors
from clevo_control.errors import ClevoError


class ParseColorTest(unittest.TestCase):
    def test_hex_forms(self):
        self.assertEqual(colors.parse_color("#FF8000"), (255, 128, 0))
        self.assertEqual(colors.parse_color("ff8000"), (255, 128, 0))
        self.assertEqual(colors.parse_color("#f80"), (255, 136, 0))
        self.assertEqual(colors.parse_color("f80"), (255, 136, 0))
        self.assertEqual(colors.parse_color("  #ff8000\n"), (255, 128, 0))

    def test_names(self):
        self.assertEqual(colors.parse_color("red"), (255, 0, 0))
        self.assertEqual(colors.parse_color("White"), (255, 255, 255))

    def test_every_name_is_a_valid_color(self):
        for name, value in colors.NAMED_COLORS.items():
            self.assertEqual(colors.format_color(colors.parse_color(name)), value)

    def test_rejects_anything_else(self):
        for bad in ("", "#", "#12345", "zzzzzz", "12345678", "bluish", "##fff", "###ffffff",
                    "ff 80 00", "１２３", "#ff80٠٠"):
            with self.assertRaises(ClevoError, msg=repr(bad)):
                colors.parse_color(bad)

    def test_format(self):
        self.assertEqual(colors.format_color((255, 128, 0)), "ff8000")


class ParseBrightnessTest(unittest.TestCase):
    def test_absolute(self):
        self.assertEqual(colors.parse_brightness("0", 255), 0)
        self.assertEqual(colors.parse_brightness("255", 255), 255)
        self.assertEqual(colors.parse_brightness(" 64 ", 255), 64)

    def test_percent(self):
        self.assertEqual(colors.parse_brightness("0%", 255), 0)
        self.assertEqual(colors.parse_brightness("50%", 255), 128)
        self.assertEqual(colors.parse_brightness("100%", 255), 255)
        self.assertEqual(colors.parse_brightness("50%", 2), 1)

    def test_rejects_anything_else(self):
        for bad in ("256", "-1", "+5", "1_0", "101%", "50 %", "%", "abc", "", "1.5", "５"):
            with self.assertRaises(ClevoError, msg=repr(bad)):
                colors.parse_brightness(bad, 255)

    def test_error_names_the_real_maximum(self):
        with self.assertRaises(ClevoError) as caught:
            colors.parse_brightness("9", 5)
        self.assertIn("0-5", str(caught.exception))


class PercentTest(unittest.TestCase):
    def test_percent_of(self):
        self.assertEqual(colors.percent_of(128, 255), 50)
        self.assertEqual(colors.percent_of(0, 255), 0)
        self.assertEqual(colors.percent_of(255, 255), 100)

    def test_zero_maximum_does_not_divide_by_zero(self):
        self.assertEqual(colors.percent_of(0, 0), 0)


if __name__ == "__main__":
    unittest.main()
