from __future__ import annotations

import pytest
from pydantic import ValidationError

from bemestar.interfaces.api.schemas import ProfileUpdate


def test_profile_rejects_hr_max_not_above_resting_hr() -> None:
    with pytest.raises(ValidationError):
        ProfileUpdate(hr_max=60, hr_rest=70)


def test_profile_accepts_valid_heart_rates() -> None:
    profile = ProfileUpdate(hr_max=190, hr_rest=60)
    assert profile.hr_max == 190
    assert profile.hr_rest == 60
