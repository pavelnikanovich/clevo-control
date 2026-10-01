# SPDX-License-Identifier: GPL-2.0-or-later
import os
import stat
import unittest

from clevo_control.errors import ClevoError
from clevo_control.state import ColorState
from tests.fakesysfs import FakeSysfsTestCase


class ColorStateTest(FakeSysfsTestCase):
    def setUp(self):
        super().setUp()
        self.cs = ColorState(self.state)

    def put(self, data):
        with open(self.state, "wb") as f:
            f.write(data)

    def test_absent(self):
        self.assertIsNone(self.cs.load())

    def test_roundtrip(self):
        self.cs.save((0, 255, 128))
        self.assertEqual(self.cs.load(), (0, 255, 128))
        with open(self.state) as f:
            self.assertEqual(f.read(), "00ff80\n")

    def test_saved_file_is_group_writable(self):
        self.cs.save((1, 2, 3))
        self.assertEqual(stat.S_IMODE(os.stat(self.state).st_mode), 0o664)

    def test_save_replaces_and_leaves_no_temporary_files(self):
        self.cs.save((1, 2, 3))
        self.cs.save((4, 5, 6))
        self.assertEqual(os.listdir(self.state_dir), ["backlight-color"])
        self.assertEqual(self.cs.load(), (4, 5, 6))

    def test_invalid_content_counts_as_absent(self):
        for data in (b"", b"\n", b"nothex\n", b"ff00\n", b"ff0000ff\n", b"FF 00 00\n",
                     b'{"color": "ff0000"}\n', b"\xff\xfe\x00\n", b"ff0000\nff0000\n"):
            self.put(data)
            self.assertIsNone(self.cs.load(), msg=repr(data))

    def test_uppercase_is_accepted(self):
        self.put(b"FF8000\n")
        self.assertEqual(self.cs.load(), (255, 128, 0))

    def test_oversized_file_is_not_read_in_full(self):
        self.put(b"ff0000" + b"0" * 10_000_000)
        self.assertIsNone(self.cs.load())

    def test_symlink_is_not_followed(self):
        target = os.path.join(self.root, "secret")
        with open(target, "w") as f:
            f.write("ff0000\n")
        os.symlink(target, self.state)
        self.assertIsNone(self.cs.load())

    def test_save_replaces_a_symlink_instead_of_writing_through_it(self):
        target = os.path.join(self.root, "victim")
        with open(target, "w") as f:
            f.write("untouched\n")
        os.symlink(target, self.state)
        self.cs.save((1, 2, 3))
        with open(target) as f:
            self.assertEqual(f.read(), "untouched\n")
        self.assertFalse(os.path.islink(self.state))

    def test_directory_instead_of_file(self):
        os.mkdir(self.state)
        self.assertIsNone(self.cs.load())

    def test_unwritable_directory(self):
        self.skip_if_root()
        os.chmod(self.state_dir, 0o555)
        self.addCleanup(os.chmod, self.state_dir, 0o755)
        with self.assertRaises(ClevoError) as caught:
            self.cs.save((1, 2, 3))
        self.assertIn("plugdev", str(caught.exception))

    def test_missing_directory(self):
        with self.assertRaises(ClevoError):
            ColorState(os.path.join(self.root, "nowhere", "backlight-color")).save((1, 2, 3))


if __name__ == "__main__":
    unittest.main()
