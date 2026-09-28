import pytest

from backend.app.rpa.actions import (
    basic,
)
from backend.app.schemas.contracts import (
    Step,
)


class FakeOptions:
    def __init__(
        self,
        values,
    ):
        self.values = values

    async def evaluate_all(
        self,
        script,
    ):
        return self.values


class FakeTarget:
    def __init__(
        self,
        options,
    ):
        self.options = options
        self.selected = None

    def locator(
        self,
        selector,
    ):
        assert selector == "option"

        return FakeOptions(
            self.options
        )

    async def select_option(
        self,
        value,
        timeout,
    ):
        self.selected = (
            value,
            timeout,
        )


def select_step():
    return Step.model_validate({
        "id":
            "step-department",
        "type":
            "select",
        "selectors": [
            {
                "kind":
                    "css",
                "value":
                    "#department",
            }
        ],
        "value":
            "{{department}}",
    })


async def test_select_existing_option(
    monkeypatch,
):
    target = FakeTarget(
        [
            "IT",
            "HR",
            "FINANCE",
        ]
    )

    async def choose(
        *args,
        **kwargs,
    ):
        return target

    monkeypatch.setattr(
        basic,
        "choose",
        choose,
    )

    await basic.perform(
        None,
        select_step(),
        {
            "department":
                "IT",
        },
        lambda *args, **kwargs:
            None,
        lambda *args, **kwargs:
            None,
    )

    assert target.selected == (
        "IT",
        10000,
    )


async def test_select_missing_option_fails_fast(
    monkeypatch,
):
    target = FakeTarget(
        [
            "IT",
            "HR",
            "FINANCE",
        ]
    )

    async def choose(
        *args,
        **kwargs,
    ):
        return target

    monkeypatch.setattr(
        basic,
        "choose",
        choose,
    )

    with pytest.raises(
        ValueError,
        match="SELECT_OPTION_NOT_FOUND",
    ):
        await basic.perform(
            None,
            select_step(),
            {
                "department":
                    "IAM",
            },
            lambda *args, **kwargs:
                None,
            lambda *args, **kwargs:
                None,
        )

    assert target.selected is None
