# SPDX-License-Identifier: GPL-2.0-or-later
import os
import shutil
import unittest

from clevo_control.errors import ClevoError
from clevo_control.profile import Profile
from tests.fakesysfs import FakeSysfsTestCase


class ProfileTest(FakeSysfsTestCase):
    def setUp(self):
        super().setUp()
        self.profile = Profile(self.profile_class)

    def test_available(self):
        self.assertTrue(self.profile.available())
        self.assertFalse(Profile(self.profile_class + "-missing").available())

    def test_only_the_clevo_handler_counts(self):
        shutil.rmtree(self.profile_dir)
        self.add_profile_handler("platform-profile-0", "thinkpad-acpi")
        self.assertFalse(self.profile.available())
        with self.assertRaises(ClevoError):
            self.profile.get()

    def test_handler_found_under_any_index(self):
        shutil.rmtree(self.profile_dir)
        self.add_profile_handler("platform-profile-0", "other")
        path = self.add_profile_handler("platform-profile-3", "clevo", profile="quiet")
        self.assertEqual(self.profile.get(), "quiet")
        self.profile.set("performance")
        self.assertEqual(self.read_profile(path), "performance")

    def test_handler_recreated_under_another_index(self):
        self.assertEqual(self.profile.get(), "balanced")
        shutil.rmtree(self.profile_dir)
        self.add_profile_handler("platform-profile-1", "clevo", profile="low-power")
        self.assertEqual(self.profile.get(), "low-power")

    def test_choices(self):
        self.assertEqual(self.profile.choices(),
                         ["low-power", "quiet", "balanced", "performance"])

    def test_set(self):
        self.profile.set("quiet")
        self.assertEqual(self.read_profile(), "quiet")

    def test_set_rejects_unknown_profile(self):
        with self.assertRaises(ClevoError) as caught:
            self.profile.set("turbo")
        self.assertIn("quiet", str(caught.exception))
        self.assertEqual(self.read_profile(), "balanced")

    def test_permission_error_names_the_group(self):
        self.skip_if_root()
        os.chmod(os.path.join(self.profile_dir, "profile"), 0o444)
        with self.assertRaises(ClevoError) as caught:
            self.profile.set("quiet")
        self.assertIn("plugdev", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
