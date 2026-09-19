from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from headsup.models import Profile


class JsonProfileStore:
    def __init__(self, path: Path):
        self.path = path

    def get(self) -> Profile:
        return Profile.model_validate_json(self.path.read_text())

    def update(self, patch: dict[str, Any]) -> Profile:
        data = json.loads(self.path.read_text())
        data.update(patch)
        profile = Profile.model_validate(data)
        self.path.write_text(profile.model_dump_json(indent=2))
        return profile
