import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.core.security import SENSITIVE, origin


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApplicationIn(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    url: str = Field(max_length=2000)
    environment: Literal["DEV", "HML", "PRD"] = "DEV"
    browser: Literal["chromium", "firefox", "chrome", "msedge"] = "chromium"
    headless: bool = True
    timeout_ms: int = Field(default=30000, ge=500, le=60000)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("url")
    @classmethod
    def valid_url(cls, value):
        origin(value)
        return value


class Selector(StrictModel):
    kind: Literal["css", "testid", "role", "label", "placeholder", "text", "xpath"] = "css"
    value: str = Field(min_length=1, max_length=1000)
    name: str | None = Field(default=None, max_length=300)


class Step(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,60}$")
    type: Literal[
        "navigate",
        "click",
        "fill",
        "wait",
        "select",
        "screenshot",
        "extract_text",
        "assert_text",
        "check",
        "press",
        "hover",
    ]
    name: str = Field(default="", max_length=120)
    enabled: bool = True
    selectors: list[Selector] = Field(default_factory=list, max_length=10)
    value: str = Field(default="", max_length=10000)
    url: str = Field(default="", max_length=2000)
    output: str = Field(default="result", pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,59}$")
    timeout_ms: int = Field(default=10000, ge=200, le=60000)
    wait_ms: int = Field(default=1000, ge=0, le=30000)
    secret: bool = False

    @model_validator(mode="after")
    def valid_step(self):
        if (
            self.type
            in {"click", "fill", "select", "extract_text", "assert_text", "check", "press", "hover"}
            and not self.selectors
        ):
            raise ValueError("Esta ação precisa de um seletor")
        if self.type == "navigate" and not self.url:
            raise ValueError("Navigate precisa de URL")
        password_target = any(SENSITIVE.search(s.value) for s in self.selectors)
        if self.type == "fill" and (self.secret or password_target):
            self.secret = True
            if not re.fullmatch(r"{{\s*[A-Za-z_][\w.]*\s*}}", self.value):
                raise ValueError(
                    "Segredos precisam de referência {{variavel}}, nunca valor literal"
                )
        return self


class WorkflowIn(StrictModel):
    application_id: str
    name: str = Field(min_length=1, max_length=120)
    operation: str = Field(default="CUSTOM", pattern=r"^[A-Z_]{1,40}$")
    timeout_seconds: int = Field(default=600, ge=5, le=3600)
    steps: list[Step] = Field(default_factory=list, max_length=200)
    revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def unique_steps(self):
        if len({s.id for s in self.steps}) != len(self.steps):
            raise ValueError("IDs de etapas duplicados")
        return self


class ExecutionIn(StrictModel):
    input: dict = Field(default_factory=dict)
    correlation_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.:-]{1,100}$")


class LoginIn(StrictModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)
