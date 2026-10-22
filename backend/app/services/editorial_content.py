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

Version timestamps are only a display order. Several versions can share a
timestamp, so approval is recorded as a pointer, and "newest" is used only to
choose among unapproved drafts.
"""

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edit_history import EditVersion
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
) -> EditVersion:
    """Record a staff final and set approval to match.

    Approving makes this exact revision the approved one. Saving without
    approval leaves the submission in review with nothing approved, so an
    older approval cannot be published while staff are mid-revision.
    """
    if "Edit_Versions" in sa.inspect(submission).unloaded:
        await session.refresh(submission, ["Edit_Versions"])
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
