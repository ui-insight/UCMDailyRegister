"""Business logic for centrally managed recurring newsletter messages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.newsletter import Newsletter, NewsletterExternalItem
from app.models.recurring_message import RecurringMessage, RecurringMessageIssueOverride
from app.models.section import NewsletterSection
from app.services import recurrence_service, schedule_service


@dataclass(slots=True)
class RecurringMessageIssueCandidate:
    Id: str
    Newsletter_Type: str
    Section_Id: str
    Headline: str
    Body: str
    Start_Date: date
    Recurrence_Type: str
    Recurrence_Interval: int
    End_Date: date | None
    Excluded_Dates: list[date]
    Is_Active: bool
    Selected: bool
    Skipped: bool


async def list_recurring_messages(
    db: AsyncSession,
    newsletter_type: str | None = None,
    active_only: bool = False,
) -> list[RecurringMessage]:
    query = (
        sa.select(RecurringMessage)
        .options(selectinload(RecurringMessage.Section_Rel))
        .order_by(RecurringMessage.Newsletter_Type, RecurringMessage.Headline)
    )
    if newsletter_type:
        query = query.where(RecurringMessage.Newsletter_Type == newsletter_type)
    if active_only:
        query = query.where(RecurringMessage.Is_Active == True)  # noqa: E712
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_recurring_message(
    db: AsyncSession,
    recurring_message_id: str,
) -> RecurringMessage | None:
    result = await db.execute(
        sa.select(RecurringMessage)
        .where(RecurringMessage.Id == recurring_message_id)
        .options(selectinload(RecurringMessage.Section_Rel))
    )
    return result.scalar_one_or_none()


async def create_recurring_message(
    db: AsyncSession,
    *,
    newsletter_type: str,
    section_id: str,
    headline: str,
    body: str,
    start_date: date,
    recurrence_type: str,
    recurrence_interval: int,
    end_date: date | None,
    excluded_dates: list[date] | None = None,
    is_active: bool = True,
) -> RecurringMessage:
    await _validate_section_for_newsletter(db, section_id, newsletter_type)
    _validate_message_range(start_date, end_date, recurrence_type)

    message = RecurringMessage(
        Newsletter_Type=newsletter_type,
        Section_Id=section_id,
        Headline=headline,
        Body=body,
        Start_Date=start_date,
        Recurrence_Type=recurrence_type,
        Recurrence_Interval=recurrence_interval,
        End_Date=end_date,
        Excluded_Dates=sorted(
            excluded_date.isoformat() for excluded_date in (excluded_dates or [])
        ),
        Is_Active=is_active,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def update_recurring_message(
    db: AsyncSession,
    recurring_message_id: str,
    **kwargs,
) -> RecurringMessage | None:
    message = await get_recurring_message(db, recurring_message_id)
    if not message:
        return None

    newsletter_type = kwargs.get("Newsletter_Type", message.Newsletter_Type)
    section_id = kwargs.get("Section_Id", message.Section_Id)
    start_date = kwargs.get("Start_Date", message.Start_Date)
    recurrence_type = kwargs.get("Recurrence_Type", message.Recurrence_Type)
    end_date = kwargs.get("End_Date", message.End_Date)

    await _validate_section_for_newsletter(db, section_id, newsletter_type)
    _validate_message_range(start_date, end_date, recurrence_type)

    if "Excluded_Dates" in kwargs and kwargs["Excluded_Dates"] is not None:
        kwargs["Excluded_Dates"] = sorted(
            excluded_date.isoformat() for excluded_date in kwargs["Excluded_Dates"]
        )

    for key, value in kwargs.items():
        if value is not None or key == "End_Date":
            setattr(message, key, value)

    await db.commit()
    await db.refresh(message)
    return message


async def delete_recurring_message(
    db: AsyncSession,
    recurring_message_id: str,
) -> bool:
    message = await get_recurring_message(db, recurring_message_id)
    if not message:
        return False
    await db.delete(message)
    await db.commit()
    return True


async def list_issue_candidates(
    db: AsyncSession,
    newsletter: Newsletter,
) -> list[RecurringMessageIssueCandidate]:
    messages = await _list_applicable_or_overridden_messages(db, newsletter)
    selected_ids = {
        item.Source_Id
        for item in newsletter.External_Items
        if item.Source_Type == "recurring_message"
    }
    skipped_ids = await _get_skipped_message_ids(db, newsletter.Id)

    candidates: list[RecurringMessageIssueCandidate] = []
    for message in messages:
        candidates.append(
            RecurringMessageIssueCandidate(
                Id=message.Id,
                Newsletter_Type=message.Newsletter_Type,
                Section_Id=message.Section_Id,
                Headline=message.Headline,
                Body=message.Body,
                Start_Date=message.Start_Date,
                Recurrence_Type=message.Recurrence_Type,
                Recurrence_Interval=message.Recurrence_Interval,
                End_Date=message.End_Date,
                Excluded_Dates=[
                    date.fromisoformat(excluded_date)
                    for excluded_date in (message.Excluded_Dates or [])
                ],
                Is_Active=message.Is_Active,
                Selected=message.Id in selected_ids,
                Skipped=message.Id in skipped_ids,
            )
        )

    return sorted(candidates, key=lambda candidate: candidate.Headline.lower())


async def sync_newsletter_recurring_messages(
    db: AsyncSession,
    newsletter: Newsletter,
) -> None:
    skipped_ids = await _get_skipped_message_ids(db, newsletter.Id)
    existing_ids = {
        item.Source_Id
        for item in newsletter.External_Items
        if item.Source_Type == "recurring_message"
    }

    messages = await _list_messages_applying_on_date(
        db,
        newsletter.Newsletter_Type,
        newsletter.Publish_Date,
    )
    for message in messages:
        if message.Id in skipped_ids or message.Id in existing_ids:
            continue
        await _insert_recurring_message_item(db, newsletter, message)

    await db.commit()


async def add_recurring_message_to_newsletter(
    db: AsyncSession,
    newsletter: Newsletter,
    recurring_message_id: str,
) -> NewsletterExternalItem | None:
    message = await get_recurring_message(db, recurring_message_id)
    if not message or not message.Is_Active:
        return None
    if message.Newsletter_Type != newsletter.Newsletter_Type:
        return None

    existing_item = next(
        (
            item
            for item in newsletter.External_Items
            if item.Source_Type == "recurring_message" and item.Source_Id == recurring_message_id
        ),
        None,
    )
    if existing_item:
        return existing_item

    await _clear_issue_override(db, newsletter.Id, recurring_message_id)
    item = await _insert_recurring_message_item(db, newsletter, message)
    await db.commit()
    await db.refresh(item)
    return item


async def skip_recurring_message_for_newsletter(
    db: AsyncSession,
    newsletter: Newsletter,
    recurring_message_id: str,
) -> bool:
    message = await get_recurring_message(db, recurring_message_id)
    if not message or message.Newsletter_Type != newsletter.Newsletter_Type:
        return False

    existing_override = await _get_issue_override(db, newsletter.Id, recurring_message_id)
    if not existing_override:
        db.add(
            RecurringMessageIssueOverride(
                Newsletter_Id=newsletter.Id,
                Recurring_Message_Id=recurring_message_id,
                Override_Action="skip",
            )
        )

    for item in list(newsletter.External_Items):
        if item.Source_Type == "recurring_message" and item.Source_Id == recurring_message_id:
            await db.delete(item)

    await db.commit()
    return True


def applies_on_date(message: RecurringMessage, publish_date: date) -> bool:
    occurrences = recurrence_service.expand_recurrence(
        anchor=message.Start_Date,
        recurrence_type=message.Recurrence_Type,
        interval=message.Recurrence_Interval,
        from_date=publish_date,
        to_date=publish_date,
        until=message.End_Date,
        excluded_dates=message.Excluded_Dates,
    )
    return publish_date in occurrences


async def _insert_recurring_message_item(
    db: AsyncSession,
    newsletter: Newsletter,
    message: RecurringMessage,
) -> NewsletterExternalItem:
    from app.services import newsletter_service

    item = await newsletter_service.add_external_item(
        db,
        newsletter_id=newsletter.Id,
        section_id=message.Section_Id,
        source_type="recurring_message",
        source_id=message.Id,
        source_url=None,
        event_start=None,
        event_end=None,
        location=None,
        final_headline=message.Headline,
        final_body=message.Body,
        commit=False,
    )
    newsletter.External_Items.append(item)
    return item


async def _validate_section_for_newsletter(
    db: AsyncSession,
    section_id: str,
    newsletter_type: str,
) -> None:
    result = await db.execute(
        sa.select(NewsletterSection).where(
            NewsletterSection.Id == section_id,
            NewsletterSection.Newsletter_Type == newsletter_type,
        )
    )
    section = result.scalar_one_or_none()
    if not section:
        raise ValueError("Section does not belong to the selected newsletter type")


def _validate_message_range(
    start_date: date,
    end_date: date | None,
    recurrence_type: str,
) -> None:
    if end_date and end_date < start_date:
        raise ValueError("End_Date cannot be before Start_Date")
    if recurrence_type == "date_range" and end_date is None:
        raise ValueError("End_Date is required for date_range recurrence")


async def _list_applicable_or_overridden_messages(
    db: AsyncSession,
    newsletter: Newsletter,
) -> list[RecurringMessage]:
    applicable = await _list_messages_applying_on_date(
        db,
        newsletter.Newsletter_Type,
        newsletter.Publish_Date,
    )
    skipped_ids = await _get_skipped_message_ids(db, newsletter.Id)
    selected_ids = {
        item.Source_Id
        for item in newsletter.External_Items
        if item.Source_Type == "recurring_message"
    }

    extra_ids = skipped_ids | selected_ids
    if not extra_ids:
        return applicable

    result = await db.execute(
        sa.select(RecurringMessage)
        .where(RecurringMessage.Id.in_(extra_ids))
        .options(selectinload(RecurringMessage.Section_Rel))
    )
    combined: dict[str, RecurringMessage] = {message.Id: message for message in applicable}
    combined.update({message.Id: message for message in result.scalars().all()})
    return list(combined.values())


async def _list_messages_applying_on_date(
    db: AsyncSession,
    newsletter_type: str,
    publish_date: date,
) -> list[RecurringMessage]:
    configs = await schedule_service.list_configs(db, newsletter_type)
    if configs:
        valid_dates = await schedule_service.get_valid_publication_dates(
            db,
            publish_date,
            publish_date,
            newsletter_type=newsletter_type,
        )
        valid_date_values = {entry["date"] for entry in valid_dates}
        if publish_date not in valid_date_values:
            return []

    result = await db.execute(
        sa.select(RecurringMessage)
        .where(
            RecurringMessage.Newsletter_Type == newsletter_type,
            RecurringMessage.Is_Active == True,  # noqa: E712
        )
        .options(selectinload(RecurringMessage.Section_Rel))
    )
    messages = list(result.scalars().all())
    return [message for message in messages if applies_on_date(message, publish_date)]


async def _get_issue_override(
    db: AsyncSession,
    newsletter_id: str,
    recurring_message_id: str,
) -> RecurringMessageIssueOverride | None:
    result = await db.execute(
        sa.select(RecurringMessageIssueOverride).where(
            RecurringMessageIssueOverride.Newsletter_Id == newsletter_id,
            RecurringMessageIssueOverride.Recurring_Message_Id == recurring_message_id,
        )
    )
    return result.scalar_one_or_none()


async def _clear_issue_override(
    db: AsyncSession,
    newsletter_id: str,
    recurring_message_id: str,
) -> None:
    override = await _get_issue_override(db, newsletter_id, recurring_message_id)
    if override:
        await db.delete(override)
        await db.flush()


async def _get_skipped_message_ids(
    db: AsyncSession,
    newsletter_id: str,
) -> set[str]:
    result = await db.execute(
        sa.select(RecurringMessageIssueOverride.Recurring_Message_Id).where(
            RecurringMessageIssueOverride.Newsletter_Id == newsletter_id,
            RecurringMessageIssueOverride.Override_Action == "skip",
        )
    )
    return set(result.scalars().all())
