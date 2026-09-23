import pytest
from pydantic import ValidationError

from backend.app.core.security import check_url, mask, seal, unseal
from backend.app.rpa.variable_engine import resolve
from backend.app.schemas.contracts import Step, WorkflowIn


def test_encrypted_input_and_masking():
    value = {"username": "joao", "password": "do-not-leak", "nested": {"access_token": "abc"}}
    encrypted = seal(value)
    assert "do-not-leak" not in encrypted
    assert unseal(encrypted) == value
    assert mask(value)["nested"]["access_token"] == "***"
    assert mask("error do-not-leak", ("do-not-leak",)) == "error ***"


def test_variables_no_eval():
    assert resolve("{{person.name}}", {"person": {"name": "Joao"}}) == "Joao"
    with pytest.raises(ValueError):
        resolve("{{missing}}", {})
    assert resolve("{{__import__('os')}}", {}) == "{{__import__('os')}}"


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://evil.local",
        "http://127.0.0.1:18081.evil.com",
        "http://u:p@127.0.0.1:18081",
    ],
)
def test_destination_restriction(url):
    with pytest.raises(ValueError):
        check_url(url)


def test_destination_allowed():
    assert check_url("http://127.0.0.1:18081/users")


def test_literal_password_rejected():
    with pytest.raises(ValidationError):
        Step(id="a", type="fill", selectors=[{"value": "#password"}], value="literal")
    assert Step(
        id="a", type="fill", selectors=[{"value": "#password"}], value="{{password}}"
    ).secret


def test_unknown_action_and_duplicate_ids():
    with pytest.raises(ValidationError):
        Step(id="a", type="javascript", value="process.exit()")
    with pytest.raises(ValidationError):
        WorkflowIn(name="bad", application_id="x", steps=[{"id": "a", "type": "wait"}] * 2)
