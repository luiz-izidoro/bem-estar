from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=500)


class ProfileUpdate(BaseModel):
    hr_max: float | None = Field(default=None, ge=80, le=260)
    hr_rest: float | None = Field(default=None, ge=25, le=140)
    trimp_exponential_coefficient: float = Field(default=1.92, ge=0.5, le=4.0)
    target_sleep_hours: float = Field(default=8.0, ge=4.0, le=12.0)
    locale: str = Field(default="pt-BR", pattern="^(pt-BR|en)$")

    @model_validator(mode="after")
    def validate_heart_rates(self) -> ProfileUpdate:
        if self.hr_max is not None and self.hr_rest is not None and self.hr_max <= self.hr_rest:
            raise ValueError("hr_max must be greater than hr_rest")
        return self
