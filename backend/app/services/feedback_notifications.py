"""Channel-neutral delivery contract for product-feedback notifications.

Phase one intentionally ships without an external transport. The disabled
implementation gives feedback capture stable delivery semantics and a narrow
adapter boundary while UCM and OIT decide which outbound channel is approved.

Notification payloads are deliberately smaller than feedback records. They do
not expose report details, browser strings, host values, submission content or
editorial notes. A future transport can alert a maintainer with enough context
to open the staff-only feedback queue without copying the report outside the
application.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.config import settings
from app.models.feedback import ProductFeedback


@dataclass(frozen=True, slots=True)
class FeedbackNotificationPayload:
    """Sanitized context that an approved notification adapter may deliver."""

    Feedback_Id: str
    Feedback_Type: str
    Summary: str
    Route: str
    App_Environment: str
    Submitted_At: datetime
    Contact_Email: str | None


class FeedbackNotifier(Protocol):
    """Transport boundary for an approved feedback-notification channel."""

    name: str
    enabled: bool

    async def send(self, payload: FeedbackNotificationPayload) -> None:
        """Deliver one sanitized notification or raise a transport error."""


class DisabledFeedbackNotifier:
    """Safe default used until UCM approves an outbound notification channel."""

    name = "disabled"
    enabled = False

    async def send(self, payload: FeedbackNotificationPayload) -> None:
        raise RuntimeError("The disabled feedback notifier cannot send messages")


_disabled_notifier = DisabledFeedbackNotifier()


def get_feedback_notifier() -> FeedbackNotifier:
    """Return the configured notifier dependency.

    Phase one supports only the disabled transport. Future adapters should be
    selected here from validated settings after institutional approval.
    """

    if settings.feedback_notification_channel == "disabled":
        return _disabled_notifier

    # Pydantic currently rejects any other configured value. Keeping this
    # guard makes the boundary fail closed if validation changes later.
    raise RuntimeError("Unsupported feedback notification channel")


def build_feedback_notification_payload(
    feedback: ProductFeedback,
) -> FeedbackNotificationPayload:
    """Build a privacy-limited notification payload from a stored report."""

    return FeedbackNotificationPayload(
        Feedback_Id=feedback.Id,
        Feedback_Type=feedback.Feedback_Type,
        Summary=feedback.Summary,
        Route=feedback.Route,
        App_Environment=feedback.App_Environment,
        Submitted_At=feedback.Created_At,
        Contact_Email=feedback.Contact_Email,
    )
