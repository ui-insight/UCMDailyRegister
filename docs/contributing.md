# Contributing

## Development Setup

1. Clone the repository and follow the [Deployment guide](deployment.md) to set up backend and frontend environments.
2. Install backend with `pip install -e ".[dev]"` (includes test and lint tools).
3. Apply migrations with `alembic upgrade head`, then seed the database with `python -m app.db.seed`.
4. Verify both servers start cleanly before making changes.

## Code Conventions

### Database Columns

All SQLAlchemy column names use **PascalCase_With_Underscores**:

```python
# Correct
Original_Headline = sa.Column(sa.Text, nullable=False)
Created_At = sa.Column(sa.DateTime, server_default=sa.func.now())

# Incorrect
original_headline = sa.Column(sa.Text, nullable=False)
created_at = sa.Column(sa.DateTime, server_default=sa.func.now())
```

### SQLAlchemy Imports

Import SQLAlchemy as `sa` and use the alias throughout:

```python
import sqlalchemy as sa
from sqlalchemy.orm import relationship
```

### Relationship Loading

Use `lazy="selectin"` for all relationships to avoid N+1 queries in async contexts:

```python
links = relationship("SubmissionLink", back_populates="submission", lazy="selectin")
```

### Docstrings

All public functions, classes, and modules require docstrings. Use Google-style format:

```python
async def get_submission(db: AsyncSession, submission_id: UUID) -> Submission:
    """Fetch a single submission by ID.

    Args:
        db: Active database session.
        submission_id: UUID of the submission to retrieve.

    Returns:
        The Submission object.

    Raises:
        HTTPException: 404 if submission not found.
    """
```

### Frontend

- Components use TypeScript with explicit prop interfaces.
- Styling uses TailwindCSS v4 utility classes with University of Idaho brand tokens (see [Branding](branding.md)).
- API calls go through dedicated client functions in `src/api/`.

## AllowedValue Pattern

When introducing a new categorical field, follow the AllowedValue pattern instead of hardcoding options:

1. **Add a new value group** in `backend/data/allowed_values/allowed_values.json` (e.g., `Priority_Level`).
2. **Insert rows** with `Value_Group`, `Code`, `Label`, `Display_Order`, `Visibility_Role`, and `Description` where applicable.
3. **Reference the group** in forms via `GET /api/v1/allowed-values?group=Priority_Level`.
4. **Validate** against allowed values in the service layer.

This keeps all categorical data in the database and makes it editable without code changes.

## Branching and Pull Requests

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/short-description
   ```
2. Make focused commits with clear messages.
3. Run tests before opening a PR:
   ```bash
   cd backend && source .venv/bin/activate
   pytest
   ```
4. Open a pull request against `main` with a description of what changed and why.
5. Address review feedback in additional commits (do not force-push over review comments).

## Running Tests

### Backend

```bash
cd backend
source .venv/bin/activate
pytest                     # all tests
pytest tests/test_api/     # API tests only
pytest -x                  # stop on first failure
pytest --cov=app           # with coverage report
```

### Frontend

```bash
cd frontend
npm test
```

!!! tip "Test Database"
    Tests use an in-memory SQLite database by default. No setup is required beyond installing dependencies.

## Adding a New API Resource

When adding a new resource (e.g., `Comment`):

1. Create the SQLAlchemy model in `backend/app/models/`.
2. Create Pydantic schemas in `backend/app/schemas/`.
3. Create a service module in `backend/app/services/`.
4. Create a route module in `backend/app/api/v1/`.
5. Register the router in `backend/app/api/v1/router.py`.
6. Generate an Alembic migration: `alembic revision --autogenerate -m "add comments"`.
7. Write tests covering CRUD operations and edge cases.
