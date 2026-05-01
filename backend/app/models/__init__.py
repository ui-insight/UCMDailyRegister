"""SQLAlchemy ORM models for the UCM Newsletter Builder.

This package defines the data model for the entire newsletter production
pipeline, from content submission through AI editing, human review, and
final newsletter assembly. All models follow the PascalCase_With_Underscores
column naming convention shared with the VERASUnlimited project.

Categorical values (submission status, newsletter type, severity, etc.) are
stored as plain sa.String(50) columns rather than hard-coded Enum types. The
AllowedValue table provides the canonical list of permitted values for each
group, enabling administrators to extend vocabularies without code changes.

Models included:
    AllowedValue             -- Controlled vocabulary lookup table
    Submission               -- Content submitted for newsletter inclusion
    SubmissionLink           -- Hyperlinks attached to a submission
    SubmissionScheduleRequest -- Submitter date/repeat preferences
    EditVersion              -- Immutable edit snapshots (original, AI, final)
    Newsletter               -- A single newsletter edition (TDR or My UI)
    NewsletterItem           -- A placed submission within a newsletter
    NewsletterExternalItem   -- Imported external item placed within a newsletter
    RecurringMessage         -- Centrally managed recurring editorial content
    RecurringMessageIssueOverride -- Issue-level skip/override markers
    ProductFeedback        -- In-app bug reports and feature ideas
    NewsletterSection        -- Section catalog (Announcements, Kudos, etc.)
    StyleRule                -- Writing-style rules for the AI pipeline
    ScheduleConfig           -- Publication cadence and deadline rules
    BlackoutDate             -- Holiday/closure non-publication dates
"""

from app.models.allowed_value import AllowedValue
from app.models.blackout_date import BlackoutDate
from app.models.custom_publish_date import CustomPublishDate
from app.models.edit_history import EditVersion
from app.models.newsletter import Newsletter, NewsletterExternalItem, NewsletterItem
from app.models.feedback import ProductFeedback
from app.models.recurring_message import RecurringMessage, RecurringMessageIssueOverride
from app.models.schedule_config import ScheduleConfig
from app.models.schedule_mode_override import ScheduleModeOverride
from app.models.section import NewsletterSection
from app.models.style_rule import StyleRule
from app.models.submission import Submission, SubmissionLink, SubmissionScheduleRequest

__all__ = [
    "AllowedValue",
    "BlackoutDate",
    "CustomPublishDate",
    "EditVersion",
    "Newsletter",
    "NewsletterExternalItem",
    "NewsletterItem",
    "ProductFeedback",
    "RecurringMessage",
    "RecurringMessageIssueOverride",
    "NewsletterSection",
    "ScheduleConfig",
    "ScheduleModeOverride",
    "StyleRule",
    "Submission",
    "SubmissionLink",
    "SubmissionScheduleRequest",
]
