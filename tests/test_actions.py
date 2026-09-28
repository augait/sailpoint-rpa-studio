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


class DynamicTarget:
    async def click(
        self,
        timeout,
    ):
        self.timeout = timeout


class DynamicPage:
    pass


async def test_selector_value_resolves_variable(
    monkeypatch,
):
    captured = {}

    async def choose(
        page,
        selectors,
        timeout_ms,
        emit,
        step_id,
    ):
        captured[
            "value"
        ] = selectors[0].value

        return DynamicTarget()

    monkeypatch.setattr(
        basic,
        "choose",
        choose,
    )

    step = Step.model_validate({
        "id":
            "edit-user",
        "type":
            "click",
        "selectors": [
            {
                "kind":
                    "xpath",
                "value":
                    (
                        "//tr[td[1][normalize-space()="
                        "'{{username}}']]//button"
                    ),
            }
        ],
    })

    await basic.perform(
        DynamicPage(),
        step,
        {
            "username":
                "joao.silva",
        },
        lambda *args, **kwargs:
            None,
        lambda *args, **kwargs:
            None,
    )

    assert captured["value"] == (
        "//tr[td[1][normalize-space()="
        "'joao.silva']]//button"
    )


async def test_selector_role_name_resolves_variable(
    monkeypatch,
):
    captured = {}

    async def choose(
        page,
        selectors,
        timeout_ms,
        emit,
        step_id,
    ):
        captured[
            "name"
        ] = selectors[0].name

        return DynamicTarget()

    monkeypatch.setattr(
        basic,
        "choose",
        choose,
    )

    step = Step.model_validate({
        "id":
            "edit-user-role",
        "type":
            "click",
        "selectors": [
            {
                "kind":
                    "role",
                "value":
                    "button",
                "name":
                    "Edit {{username}}",
            }
        ],
    })

    await basic.perform(
        DynamicPage(),
        step,
        {
            "username":
                "joao.silva",
        },
        lambda *args, **kwargs:
            None,
        lambda *args, **kwargs:
            None,
    )

    assert (
        captured["name"]
        == "Edit joao.silva"
    )


class TableCell:
    def __init__(
        self,
        value,
    ):
        self.value = value

    async def count(
        self,
    ):
        return 1

    async def inner_text(
        self,
        timeout,
    ):
        return self.value


class TableRow:
    def __init__(
        self,
        values,
    ):
        self.values = values

    def locator(
        self,
        selector,
    ):
        return TableCell(
            self.values[
                selector
            ]
        )


class TableRows:
    def __init__(
        self,
        rows,
    ):
        self.rows = rows

    async def count(
        self,
    ):
        return len(
            self.rows
        )

    def nth(
        self,
        index,
    ):
        return TableRow(
            self.rows[index]
        )


class TableContainer:
    def __init__(
        self,
        rows,
    ):
        self.rows = rows

    def locator(
        self,
        selector,
    ):
        assert selector == "tr"

        return TableRows(
            self.rows
        )


async def test_extract_table_returns_structured_rows(
    monkeypatch,
):
    container = TableContainer([
        {
            "td:nth-child(1)":
                "john.doe",
            "td:nth-child(2)":
                "John Doe",
            "td:nth-child(3)":
                "john@example.test",
        },
        {
            "td:nth-child(1)":
                "jane.doe",
            "td:nth-child(2)":
                "Jane Doe",
            "td:nth-child(3)":
                "jane@example.test",
        },
    ])

    async def choose(
        *args,
        **kwargs,
    ):
        return container

    monkeypatch.setattr(
        basic,
        "choose",
        choose,
    )

    step = Step.model_validate({
        "id":
            "aggregate-accounts",
        "type":
            "extract_table",
        "selectors": [
            {
                "kind":
                    "css",
                "value":
                    "#accounts",
            }
        ],
        "row_selector":
            "tr",
        "columns": {
            "username":
                "td:nth-child(1)",
            "displayName":
                "td:nth-child(2)",
            "email":
                "td:nth-child(3)",
        },
        "output":
            "accounts",
    })

    variables = {}

    result = await basic.perform(
        None,
        step,
        variables,
        lambda *args, **kwargs:
            None,
        lambda *args, **kwargs:
            None,
    )

    expected = [
        {
            "username":
                "john.doe",
            "displayName":
                "John Doe",
            "email":
                "john@example.test",
        },
        {
            "username":
                "jane.doe",
            "displayName":
                "Jane Doe",
            "email":
                "jane@example.test",
        },
    ]

    assert result == {
        "accounts":
            expected,
    }

    assert (
        variables["accounts"]
        == expected
    )


def test_extract_table_requires_columns():
    import pytest

    with pytest.raises(
        ValueError,
        match=(
            "Extract table precisa "
            "de colunas"
        ),
    ):
        Step.model_validate({
            "id":
                "bad-table",
            "type":
                "extract_table",
            "selectors": [
                {
                    "kind":
                        "css",
                    "value":
                        "#accounts",
                }
            ],
        })
