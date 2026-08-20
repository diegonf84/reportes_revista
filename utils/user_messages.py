"""User-facing flash message helpers.

Phase 4 (lean) — item 6: separate user-facing functional message from
technical diagnostic details. These helpers ensure that no Python
exception, file path, or class name is ever leaked into the user-visible
flash message. Technical details are logged server-side via the Flask
application logger so operators can still diagnose.

Use ``flash_user_error`` for any ``flash(..., 'error')`` call site that
previously embedded ``str(exception)`` in the message — replace the leak
with a functional summary and pass the exception as ``technical=``.
"""
from __future__ import annotations

from typing import Optional

from flask import current_app, flash


def flash_user_error(message: str, technical: Optional[BaseException] = None) -> None:
    """Flash a user-facing error message and log the technical detail.

    Args:
        message: Functional, user-facing summary. Must NOT contain
            exception class names, file paths, or technical jargon.
        technical: Optional exception to log server-side for operators.
            Its ``str()`` is never shown to the user.
    """
    if technical is not None:
        current_app.logger.exception(
            "User-facing error: %s",
            message,
            exc_info=technical,
        )
    flash(message, "danger")


def flash_user_success(message: str) -> None:
    """Flash a user-facing success message."""
    flash(message, "success")
