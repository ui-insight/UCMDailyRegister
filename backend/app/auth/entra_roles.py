"""Map Entra App Role / group names onto this app's signed-in roles.

The names live in config (`ENTRA_GROUP_STAFF` / `_SLC` / `_OPS`), never here,
so OIT renaming a role is a config change. Settings are read inside the
function rather than at import so tests can monkeypatch them.
"""

from collections.abc import Iterable

from app.auth.identity import SignedInRole
from app.config import settings


def _names(raw: str) -> set[str]:
    """Split one config value: a single name or a comma-separated list."""
    return {name.strip().casefold() for name in raw.split(",") if name.strip()}


def map_groups_to_role(claim_values: Iterable[object]) -> SignedInRole | None:
    """Resolve Entra names to a role, or `None` when none of them grant one.

    Highest privilege first: `staff` passes every gate in `app.api.deps`, so a
    user in both the staff and SLC groups is staff, not whichever Entra
    happened to list first.
    """
    held = {str(value).casefold() for value in claim_values}
    ordered: tuple[tuple[SignedInRole, str], ...] = (
        ("staff", settings.entra_group_staff),
        ("slc", settings.entra_group_slc),
        ("ops", settings.entra_group_ops),
    )
    for role, configured in ordered:
        if held & _names(configured):
            return role
    # No default role. Anonymous users already have "public" without signing
    # in; a signed-in user in no mapped group is a refused login, never a
    # silent downgrade.
    return None
