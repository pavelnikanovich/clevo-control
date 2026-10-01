# SPDX-License-Identifier: GPL-2.0-or-later
"""Builds fake sysfs trees for the LED and platform-profile class devices."""
import os
import tempfile
import unittest


class FakeSysfsTestCase(unittest.TestCase):
    """Test case with a fake LED, a fake platform-profile class and a state directory."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name

        self.led = os.path.join(self.root, "leds", "rgb:kbd_backlight")
        os.makedirs(self.led)
        self.write_led("max_brightness", "255\n")
        self.write_led("brightness", "128\n")
        self.write_led("multi_index", "red green blue\n")
        self.write_led("multi_intensity", "255 255 255\n")

        self.profile_class = os.path.join(self.root, "platform-profile")
        self.profile_dir = self.add_profile_handler("platform-profile-0", "clevo")

        self.state_dir = os.path.join(self.root, "state")
        os.mkdir(self.state_dir)
        self.state = os.path.join(self.state_dir, "backlight-color")

    def write_led(self, name, text):
        with open(os.path.join(self.led, name), "w") as f:
            f.write(text)

    def read_led(self, name):
        with open(os.path.join(self.led, name)) as f:
            return f.read()

    def add_profile_handler(self, entry, name, profile="balanced",
                            choices="low-power quiet balanced performance"):
        path = os.path.join(self.profile_class, entry)
        os.makedirs(path)
        for attr, text in (("name", name), ("choices", choices), ("profile", profile)):
            with open(os.path.join(path, attr), "w") as f:
                f.write(text + "\n")
        return path

    def read_profile(self, path=None):
        with open(os.path.join(path or self.profile_dir, "profile")) as f:
            return f.read().strip()

    def skip_if_root(self):
        if os.geteuid() == 0:
            self.skipTest("permission checks do not apply to root")
