import pytest

from backend.app.rpa.condition_engine import (
    ConditionSyntaxError,
    ConditionTypeError,
    evaluate_condition,
)


def test_condition_string_equality():
    assert evaluate_condition(
        '{{department}} == "IT"',
        {"department": "IT"},
    )


def test_condition_nested_variable():
    assert evaluate_condition(
        '{{identity.status}} != "disabled"',
        {
            "identity": {
                "status": "active",
            }
        },
    )


def test_condition_numeric_comparison():
    assert evaluate_condition(
        "{{amount}} >= 100",
        {"amount": 125},
    )


def test_condition_boolean():
    assert evaluate_condition(
        "{{enabled}} == true",
        {"enabled": True},
    )


def test_condition_null():
    assert evaluate_condition(
        "{{manager}} == null",
        {"manager": None},
    )


def test_condition_rejects_code():
    with pytest.raises(
        ConditionSyntaxError
    ):
        evaluate_condition(
            '__import__("os").system("id")',
            {},
        )


def test_condition_rejects_incompatible_ordering():
    with pytest.raises(
        ConditionTypeError
    ):
        evaluate_condition(
            "{{amount}} > 10",
            {"amount": "100"},
        )


def test_condition_missing_variable():
    with pytest.raises(
        ValueError,
        match="Variável ausente",
    ):
        evaluate_condition(
            '{{department}} == "IT"',
            {},
        )
