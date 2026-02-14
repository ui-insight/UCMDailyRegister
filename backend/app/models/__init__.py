# Import all models so they register with Base.metadata
from app.models.edit_history import EditVersion
from app.models.newsletter import Newsletter, NewsletterItem
from app.models.schedule_config import ScheduleConfig
from app.models.section import NewsletterSection
from app.models.style_rule import StyleRule
from app.models.submission import Submission, SubmissionLink, SubmissionScheduleRequest

__all__ = [
    "EditVersion",
    "Newsletter",
    "NewsletterItem",
    "NewsletterSection",
    "ScheduleConfig",
    "StyleRule",
    "Submission",
    "SubmissionLink",
    "SubmissionScheduleRequest",
]
