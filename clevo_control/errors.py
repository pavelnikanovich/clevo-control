# SPDX-License-Identifier: GPL-2.0-or-later
"""The one exception type of the package."""

GROUP = "plugdev"


class ClevoError(Exception):
    """A setting could not be read or changed; the message is fit to show to the user."""


def from_oserror(action: str, error: OSError) -> ClevoError:
    """Turn an OSError into a ClevoError, pointing at the group when access is denied."""
    reason = error.strerror or str(error)
    if isinstance(error, PermissionError):
        reason += f" (are you a member of the '{GROUP}' group?)"
    return ClevoError(f"cannot {action}: {reason}")
