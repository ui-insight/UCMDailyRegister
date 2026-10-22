"""Retention inventory counts dependencies without disclosing or deleting data."""

from datetime import date, datetime

import sqlalchemy as sa

from app.governance.retention_preview import preview
from app.models.newsletter import Newsletter, NewsletterItem
from app.models.section import NewsletterSection
from app.models.submission import Submission


async def test_inventory_preserves_sources_and_published_dependencies(db):
    section = NewsletterSection(Newsletter_Type='tdr', Name='News', Slug='news', Display_Order=1)
    issue = Newsletter(Newsletter_Type='tdr', Publish_Date=date(2024, 1, 1), Status='published')
    old = Submission(Category='faculty_staff', Target_Newsletter='tdr',
                     Original_Headline='Private source', Original_Body='Private body',
                     Submitter_Name='Person', Submitter_Email='private@example.test',
                     Image_Path='private-path.jpg', Updated_At=datetime(2023, 1, 1))
    boundary = Submission(Category='faculty_staff', Target_Newsletter='tdr',
                          Original_Headline='Boundary', Original_Body='Body',
                          Submitter_Name='Other', Submitter_Email='other@example.test',
                          Updated_At=datetime(2024, 7, 1))
    db.add_all([section, issue, old, boundary])
    await db.flush()
    db.add(NewsletterItem(Newsletter_Id=issue.Id, Submission_Id=old.Id, Section_Id=section.Id,
                          Final_Headline='Published', Final_Body='Published copy'))
    await db.commit()
    result = await preview(db, date(2024, 7, 1))
    assert result['aged_submissions'] == 1
    assert result['aged_sources_with_issue_references'] == 1
    assert result['aged_sources_with_image_references'] == 1
    assert result['disposal_authorized'] is False
    assert 'private' not in str(result)
    assert await db.scalar(sa.select(sa.func.count()).select_from(Submission)) == 2
    assert await db.scalar(sa.select(sa.func.count()).select_from(NewsletterItem)) == 1
