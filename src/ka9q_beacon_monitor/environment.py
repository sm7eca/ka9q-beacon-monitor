"""Shared registry for KA9Q-prefixed process environment names.

Runtime configuration remains owned by ``config.settings``.  Other modules may
also own explicit KA9Q-prefixed process metadata.  This module provides the
cross-module names that must be recognized by the configuration namespace
validator without turning them into runtime-configuration overrides.
"""

from __future__ import annotations


KA9Q_BUILD_VERSION_ENV = "KA9Q_BUILD_VERSION"
KA9Q_BUILD_REVISION_ENV = "KA9Q_BUILD_REVISION"
KA9Q_BUILD_TIME_UTC_ENV = "KA9Q_BUILD_TIME_UTC"

OBSERVABILITY_ENV_KEYS = frozenset(
    {
        KA9Q_BUILD_VERSION_ENV,
        KA9Q_BUILD_REVISION_ENV,
        KA9Q_BUILD_TIME_UTC_ENV,
    }
)
