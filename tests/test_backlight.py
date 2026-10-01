# SPDX-License-Identifier: GPL-2.0-or-later
import os
import unittest

from clevo_control.backlight import Backlight
from clevo_control.errors import ClevoError
from tests.fakesysfs import FakeSysfsTestCase


class BacklightTest(FakeSysfsTestCase):
    def setUp(self):
        super().setUp()
        self.bl = Backlight(self.led)

    def test_available(self):
        self.assertTrue(self.bl.available())
        self.assertFalse(Backlight(self.led + "-missing").available())

    def test_missing_device_names_the_module(self):
        with self.assertRaises(ClevoError) as caught:
            Backlight(self.led + "-missing").get_color()
        self.assertIn("clevo-control", str(caught.exception))

    def test_color_roundtrip(self):
        self.bl.set_color((255, 128, 0))
        self.assertEqual(self.read_led("multi_intensity").split(), ["255", "128", "0"])
        self.assertEqual(self.bl.get_color(), (255, 128, 0))

    def test_color_honours_channel_order(self):
        self.write_led("multi_index", "blue green red\n")
        self.bl.set_color((255, 128, 0))
        self.assertEqual(self.read_led("multi_intensity").split(), ["0", "128", "255"])
        self.assertEqual(self.bl.get_color(), (255, 128, 0))

    def test_intensities_above_255_read_as_255(self):
        self.write_led("multi_intensity", "999 0 0\n")
        self.assertEqual(self.bl.get_color(), (255, 0, 0))

    def test_unexpected_channels(self):
        self.write_led("multi_index", "red green white\n")
        with self.assertRaises(ClevoError):
            self.bl.get_color()

    def test_malformed_intensity(self):
        for text in ("255 255\n", "a b c\n", "\n", "1 2 3 4\n", "-1 0 0\n"):
            self.write_led("multi_intensity", text)
            with self.assertRaises(ClevoError, msg=repr(text)):
                self.bl.get_color()

    def test_brightness_roundtrip(self):
        self.bl.set_brightness(64)
        self.assertEqual(self.bl.get_brightness(), 64)
        self.assertEqual(self.bl.max_brightness(), 255)

    def test_brightness_out_of_range(self):
        for level in (-1, 256):
            with self.assertRaises(ClevoError):
                self.bl.set_brightness(level)
        self.assertEqual(self.read_led("brightness").strip(), "128")

    def test_malformed_brightness(self):
        self.write_led("brightness", "bright\n")
        with self.assertRaises(ClevoError):
            self.bl.get_brightness()

    def test_undecodable_content_is_an_error_not_an_exception(self):
        with open(os.path.join(self.led, "brightness"), "wb") as f:
            f.write(b"\xff\xfe\n")
        with self.assertRaises(ClevoError):
            self.bl.get_brightness()

    def test_permission_error_names_the_group(self):
        self.skip_if_root()
        os.chmod(os.path.join(self.led, "multi_intensity"), 0o444)
        with self.assertRaises(ClevoError) as caught:
            self.bl.set_color((1, 2, 3))
        self.assertIn("plugdev", str(caught.exception))

    def test_unreadable_attribute(self):
        self.skip_if_root()
        os.chmod(os.path.join(self.led, "brightness"), 0o000)
        with self.assertRaises(ClevoError):
            self.bl.get_brightness()


if __name__ == "__main__":
    unittest.main()
