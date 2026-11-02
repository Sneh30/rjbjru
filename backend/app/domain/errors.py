"""Typed domain errors mapped to RFC 7807 problem documents at the API boundary."""

from __future__ import annotations


class WindLensError(Exception):
    """Base class for expected, user-facing failures.

    Args:
        message: Human-readable detail for the problem document.
        extra: Additional machine-readable fields merged into the problem body.
    """

    def __init__(self, message: str, *, extra: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.extra: dict[str, object] = extra or {}


class OutOfScopeError(WindLensError):
    """A requested date or instant is outside the configured evaluation window."""


class NoDataError(WindLensError):
    """No eligible data exists for the requested view."""


class DataIntegrityError(WindLensError):
    """A snapshot invariant or a no-leakage post-condition failed."""


class DataUnavailableError(WindLensError):
    """The committed snapshot could not be loaded, so request data is unavailable."""


class ConfigError(WindLensError):
    """Configuration is internally inconsistent."""
