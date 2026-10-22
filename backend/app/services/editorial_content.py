"""Which revision of a submission's text is authoritative.

A submission accumulates EditVersion rows: the submitted original, AI
suggestions, and staff finals. The Editor, newsletter assembly and export
must agree on which one they use, so the precedence lives here and nowhere
else:

- The approved revision is the one staff explicitly approved
  (Submission.Approved_Version_Id). Assembly publishes it.
- The working revision is what the Editor opens: the approved revision,
  else the newest staff final, else the newest AI suggestion, else the
  original snapshot.
- The staff revision is the newest staff final. A save names the staff
  revision it was based on; if another save has landed since, it is
  rejected as stale rather than quietly superseding newer work. AI
  suggestions never change it.
- An edition item's copy is a snapshot taken at assembly. When the approved
  revision later changes, the item reports an upstream change; staff either
  refresh the copy from it or keep the edition copy. Nothing is overwritten
  without that choice.

Version timestamps are only a display order. Several versions can share a
timestamp, so approval is recorded as a pointer, and "newest" is used only to
choose among unapproved drafts.
"""

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edit_history import EditVersion
from app.models.newsletter import NewsletterItem
from app.models.submission import Submission

# Staff work outranks AI suggestions, which outrank the untouched original.
_DRAFT_PRECEDENCE = ("editor_final", "ai_suggested", "original")


def approved_revision(submission: Submission) -> EditVersion | None:
    """The revision staff approved for publication, if any."""
    if submission.Approved_Version_Id is None:
        return None
    for version in submission.Edit_Versions:
        if version.Id == submission.Approved_Version_Id:
            return version
    return None


def _newest(submission: Submission, version_type: str) -> EditVersion | None:
    candidates = [v for v in submission.Edit_Versions if v.Version_Type == version_type]
    if not candidates:
        return None
    # Id breaks timestamp ties so the choice is at least deterministic.
    return max(candidates, key=lambda v: (v.Created_At, v.Id))


def staff_revision(submission: Submission) -> EditVersion | None:
    """The newest staff final: what a new save must be based on."""
    return _newest(submission, "editor_final")


class StaleRevision(Exception):
    """A save was based on an older staff revision than the current one."""

    def __init__(self, current: EditVersion | None):
        super().__init__("A newer staff revision was saved.")
        self.current = current


def working_revision(submission: Submission) -> EditVersion | None:
    """The revision the Editor should open; None when no versions exist yet."""
    approved = approved_revision(submission)
    if approved is not None:
        return approved
    for version_type in _DRAFT_PRECEDENCE:
        version = _newest(submission, version_type)
        if version is not None:
            return version
    return None


def publishable_text(submission: Submission) -> tuple[str, str, str | None]:
    """Headline, body and source version ID for placing a submission in an edition.

    Prefers the approved revision. Submissions approved without one (system
    imports, or approvals recorded before the pointer existed) fall back to
    the working revision, then to the submitted text with no source version.
    """
    version = working_revision(submission)
    if version is None:
        return submission.Original_Headline, submission.Original_Body, None
    return version.Headline, version.Body, version.Id


async def save_final(
    session: AsyncSession,
    submission: Submission,
    *,
    headline: str,
    body: str,
    headline_case: str | None,
    approve: bool,
    base_revision_id: str | None = None,
    check_base: bool = False,
) -> EditVersion:
    """Record a staff final and set approval to match.

    Approving makes this exact revision the approved one. Saving without
    approval leaves the submission in review with nothing approved, so an
    older approval cannot be published while staff are mid-revision.

    With ``check_base``, raises StaleRevision when ``base_revision_id`` is
    not the current staff revision, saving nothing.
    """
    if "Edit_Versions" in sa.inspect(submission).unloaded:
        await session.refresh(submission, ["Edit_Versions"])
    if check_base:
        current = staff_revision(submission)
        if (current.Id if current else None) != base_revision_id:
            raise StaleRevision(current)
    if not any(v.Version_Type == "original" for v in submission.Edit_Versions):
        # Snapshot the original so the timeline is complete even for purely
        # manual edits.
        submission.Edit_Versions.append(
            EditVersion(
                Version_Type="original",
                Headline=submission.Original_Headline,
                Body=submission.Original_Body,
            )
        )

    version = EditVersion(
        Version_Type="editor_final",
        Headline=headline,
        Body=body,
        Headline_Case=headline_case,
    )
    submission.Edit_Versions.append(version)
    await session.flush()

    submission.Approved_Version_Id = version.Id if approve else None
    submission.Status = "approved" if approve else "in_review"
    return version


def upstream_change(item: NewsletterItem) -> EditVersion | None:
    """The approved revision an item's copy does not reflect, unless staff kept theirs."""
    state = sa.inspect(item)
    if "Submission_Rel" in state.unloaded or item.Submission_Rel is None:
        return None
    if "Edit_Versions" in sa.inspect(item.Submission_Rel).unloaded:
        return None
    approved = approved_revision(item.Submission_Rel)
    if approved is None or approved.Id in (item.Source_Version_Id, item.Upstream_Reviewed_Version_Id):
        return None
    return approved


class NoApprovedRevision(Exception):
    """The item's submission has no approved revision to refresh from."""


def refresh_from_approved(item: NewsletterItem) -> None:
    """Replace an item's copy with its submission's approved revision."""
    approved = approved_revision(item.Submission_Rel) if item.Submission_Rel else None
    if approved is None:
        raise NoApprovedRevision
    item.Final_Headline = approved.Headline
    item.Final_Body = approved.Body
    item.Source_Version_Id = approved.Id
    item.Edition_Edited = False
    item.Upstream_Reviewed_Version_Id = None


def keep_edition_copy(item: NewsletterItem) -> None:
    """Keep the item's copy and stop flagging the current approved revision."""
    approved = approved_revision(item.Submission_Rel) if item.Submission_Rel else None
    if approved is None:
        raise NoApprovedRevision
    item.Upstream_Reviewed_Version_Id = approved.Id
