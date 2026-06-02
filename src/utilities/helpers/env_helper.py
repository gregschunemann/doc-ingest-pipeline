"""EnvHelper stub for spec 0001.

This is a minimal placeholder. The full ``EnvHelper`` (parsing every
configuration knob the parent accelerator supports) is ported in spec 0002.
For now we expose only the fields that the function entry points must reach
in order to register themselves, and raise an explicit ``AttributeError``
for every other lookup so that callers fail loudly instead of silently
reading ``None``.
"""

from __future__ import annotations

import os
from typing import Any

# Default values mirror the parent accelerator's expectations.
_DEFAULTS: dict[str, Any] = {
    "DOCUMENT_PROCESSING_QUEUE_NAME": "doc-processing",
    "AZURE_BLOB_CONTAINER_NAME": "documents",
    "AZURE_BLOB_ACCOUNT_NAME": "",
    "AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION": "false",
    "MANAGED_IDENTITY_CLIENT_ID": "",
}

# Fields that are explicitly exposed on the stub. Adding a field here without
# also adding it to ``_DEFAULTS`` is a programming error.
_ALLOWED_FIELDS: frozenset[str] = frozenset(_DEFAULTS.keys())


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


class EnvHelper:
    """Read configuration from environment variables.

    Only the fields listed in :data:`_ALLOWED_FIELDS` are supported. All
    other attribute lookups raise ``AttributeError`` with a pointer to
    spec 0002 so the caller knows where the full implementation lives.
    """

    def __init__(self) -> None:
        for name, default in _DEFAULTS.items():
            object.__setattr__(self, name, os.environ.get(name, default))

        # Coerce the one boolean we care about.
        object.__setattr__(
            self,
            "AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION",
            _as_bool(self.AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION),
        )

    def __getattr__(self, name: str) -> Any:
        # ``__getattr__`` only fires when normal lookup fails, so reaching
        # this branch means the field is not in ``_ALLOWED_FIELDS``.
        raise AttributeError(
            f"{name!r} is not exposed by the spec-0001 EnvHelper stub. "
            "The full EnvHelper is ported in spec 0002."
        )

    def is_auth_type_keys(self) -> bool:
        """Return ``True`` when the caller should use key-based auth.

        The spec-0001 stub is managed-identity-only (DEC-005). The method
        exists so the ported entry points can call it during smoke tests
        without raising ``AttributeError``.
        """
        return False
