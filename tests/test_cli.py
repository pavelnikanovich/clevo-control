# SPDX-License-Identifier: GPL-2.0-or-later
import contextlib
import io
import os
import shutil
import subprocess
import sys
import unittest
from unittest import mock

from clevo_control import cli
from tests.fakesysfs import FakeSysfsTestCase

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CliTestCase(FakeSysfsTestCase):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {
            "CLEVO_CONTROL_LED": self.led,
            "CLEVO_CONTROL_PROFILE_CLASS": self.profile_class,
            "CLEVO_CONTROL_STATE": self.state,
        })
        env.start()
        self.addCleanup(env.stop)

    def run_cli(self, *args):
        """Return (exit status, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                status = cli.main(list(args))
            except SystemExit as e:  # argparse
                status = e.code
        return status, out.getvalue(), err.getvalue()

    def assert_fails(self, *args, mentions):
        status, out, err = self.run_cli(*args)
        self.assertEqual(status, 1, msg=err)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("clevoctl: "), msg=err)
        self.assertEqual(err.count("\n"), 1, msg=err)
        self.assertNotIn("Traceback", err)
        self.assertIn(mentions, err)


class StatusTest(CliTestCase):
    def test_everything_present(self):
        with open(self.state, "w") as f:
            f.write("00ff00\n")
        status, out, err = self.run_cli("status")
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(out, "backlight:\n"
                              "  color: #ffffff\n"
                              "  brightness: 128/255 (50%)\n"
                              "  saved: #00ff00\n"
                              "profile: balanced\n")

    def test_nothing_saved(self):
        _, out, _ = self.run_cli("status")
        self.assertIn("  saved: none\n", out)

    def test_devices_absent(self):
        shutil.rmtree(self.led)
        shutil.rmtree(self.profile_class)
        status, out, err = self.run_cli("status")
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(out, "backlight: not available\nprofile: not available\n")

    def test_broken_attribute_is_an_error_not_a_traceback(self):
        self.write_led("multi_intensity", "1 2\n")
        self.assert_fails("status", mentions="multi_intensity")

    def test_zero_maximum(self):
        self.write_led("max_brightness", "0\n")
        self.write_led("brightness", "0\n")
        status, out, _ = self.run_cli("status")
        self.assertEqual(status, 0)
        self.assertIn("  brightness: 0/0 (0%)\n", out)


class BacklightCommandTest(CliTestCase):
    def test_color_sets_and_saves(self):
        status, out, err = self.run_cli("backlight", "color", "orange")
        self.assertEqual((status, out, err), (0, "", ""))
        self.assertEqual(self.read_led("multi_intensity").split(), ["255", "128", "0"])
        with open(self.state) as f:
            self.assertEqual(f.read(), "ff8000\n")

    def test_color_invalid(self):
        self.assert_fails("backlight", "color", "nonsense", mentions="invalid color")
        self.assertEqual(self.read_led("multi_intensity").split(), ["255", "255", "255"])

    def test_color_set_but_not_saved(self):
        self.skip_if_root()
        os.chmod(self.state_dir, 0o555)
        self.addCleanup(os.chmod, self.state_dir, 0o755)
        self.assert_fails("backlight", "color", "red", mentions="color set, but")
        self.assertEqual(self.read_led("multi_intensity").split(), ["255", "0", "0"])

    def test_brightness(self):
        self.assertEqual(self.run_cli("backlight", "brightness", "25%")[0], 0)
        self.assertEqual(self.read_led("brightness").strip(), "64")
        self.assertEqual(self.run_cli("backlight", "brightness", "200")[0], 0)
        self.assertEqual(self.read_led("brightness").strip(), "200")

    def test_brightness_invalid(self):
        self.assert_fails("backlight", "brightness", "300", mentions="0-255")

    def test_off_and_on(self):
        self.assertEqual(self.run_cli("backlight", "off")[0], 0)
        self.assertEqual(self.read_led("brightness").strip(), "0")
        self.assertEqual(self.run_cli("backlight", "on")[0], 0)
        self.assertEqual(self.read_led("brightness").strip(), "127")

    def test_on_keeps_a_nonzero_brightness(self):
        self.write_led("brightness", "10\n")
        self.run_cli("backlight", "on")
        self.assertEqual(self.read_led("brightness").strip(), "10")

    def test_on_with_tiny_maximum_still_turns_on(self):
        self.write_led("max_brightness", "1\n")
        self.write_led("brightness", "0\n")
        self.run_cli("backlight", "on")
        self.assertEqual(self.read_led("brightness").strip(), "1")

    def test_save_remembers_the_current_color(self):
        self.write_led("multi_intensity", "0 255 255\n")
        self.assertEqual(self.run_cli("backlight", "save")[0], 0)
        with open(self.state) as f:
            self.assertEqual(f.read(), "00ffff\n")

    def test_save_failure_does_not_claim_the_color_was_set(self):
        self.skip_if_root()
        os.chmod(self.state_dir, 0o555)
        self.addCleanup(os.chmod, self.state_dir, 0o755)
        status, _, err = self.run_cli("backlight", "save")
        self.assertEqual(status, 1)
        self.assertNotIn("color set", err)

    def test_restore_applies_the_saved_color_only(self):
        with open(self.state, "w") as f:
            f.write("0000ff\n")
        self.assertEqual(self.run_cli("backlight", "restore")[0], 0)
        self.assertEqual(self.read_led("multi_intensity").split(), ["0", "0", "255"])
        self.assertEqual(self.read_led("brightness").strip(), "128")

    def test_restore_with_nothing_saved_succeeds(self):
        self.assertEqual(self.run_cli("backlight", "restore"), (0, "", ""))
        self.assertEqual(self.read_led("multi_intensity").split(), ["255", "255", "255"])

    def test_restore_ignores_corrupt_state(self):
        with open(self.state, "w") as f:
            f.write("[" * 100000)
        self.assertEqual(self.run_cli("backlight", "restore"), (0, "", ""))

    def test_missing_device(self):
        shutil.rmtree(self.led)
        self.assert_fails("backlight", "color", "red", mentions="clevo-control")


class ProfileCommandTest(CliTestCase):
    def test_get(self):
        self.assertEqual(self.run_cli("profile", "get"), (0, "balanced\n", ""))

    def test_list_marks_the_active_profile(self):
        status, out, _ = self.run_cli("profile", "list")
        self.assertEqual(status, 0)
        self.assertEqual(out, "  low-power\n  quiet\n* balanced\n  performance\n")

    def test_set(self):
        self.assertEqual(self.run_cli("profile", "set", "quiet"), (0, "", ""))
        self.assertEqual(self.read_profile(), "quiet")

    def test_set_invalid(self):
        self.assert_fails("profile", "set", "turbo", mentions="invalid profile")

    def test_not_available(self):
        shutil.rmtree(self.profile_class)
        self.assert_fails("profile", "get", mentions="not available")


class UsageTest(CliTestCase):
    def test_no_command_is_a_usage_error(self):
        self.assertEqual(self.run_cli()[0], 2)
        self.assertEqual(self.run_cli("backlight")[0], 2)
        self.assertEqual(self.run_cli("backlight", "color")[0], 2)
        self.assertEqual(self.run_cli("frobnicate")[0], 2)

    def test_version(self):
        status, out, _ = self.run_cli("--version")
        self.assertEqual(status, 0)
        with open(os.path.join(REPO, "VERSION")) as f:
            self.assertEqual(out, f"clevoctl {f.read().strip()}\n")

    def test_closed_pipe_is_not_a_traceback(self):
        result = subprocess.run(
            f"{sys.executable} {os.path.join(REPO, 'bin', 'clevoctl')} profile list | true",
            shell=True, capture_output=True, text=True, check=False)
        self.assertEqual(result.stderr, "")

    def test_script_runs_from_the_source_tree(self):
        result = subprocess.run([sys.executable, os.path.join(REPO, "bin", "clevoctl"), "status"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("backlight:", result.stdout)


if __name__ == "__main__":
    unittest.main()
