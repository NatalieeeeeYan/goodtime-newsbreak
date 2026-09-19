from datetime import datetime, timezone

import pytest
from pydantic_ai import models

models.ALLOW_MODEL_REQUESTS = False


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 9, 26, 8, 0, tzinfo=timezone.utc)
