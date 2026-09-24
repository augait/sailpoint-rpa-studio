import json
import re
from typing import Any


class ConditionSyntaxError(ValueError):
    pass


class ConditionTypeError(ValueError):
    pass


VARIABLE = r"\{\{\s*([A-Za-z_][\w.]*)\s*\}\}"

EXPRESSION = re.compile(
    rf"""
    ^\s*
    {VARIABLE}
    \s*
    (==|!=|>=|<=|>|<)
    \s*
    (.+?)
    \s*$
    """,
    re.VERBOSE,
)


def _variable_value(
    path: str,
    variables: dict[str, Any],
) -> Any:
    value: Any = variables

    for part in path.split("."):
        if (
            not isinstance(value, dict)
            or part not in value
        ):
            raise ValueError(
                f"Variável ausente: {path}"
            )

        value = value[part]

    if isinstance(value, (dict, list)):
        raise ConditionTypeError(
            "CONDITION aceita apenas valores escalares"
        )

    return value


def _literal_value(text: str) -> Any:
    value = text.strip()

    if not value:
        raise ConditionSyntaxError(
            "Literal ausente"
        )

    lowered = value.lower()

    if lowered == "true":
        return True

    if lowered == "false":
        return False

    if lowered == "null":
        return None

    #
    # Strings precisam estar entre aspas.
    #
    if (
        len(value) >= 2
        and value[0] in {'"', "'"}
        and value[-1] == value[0]
    ):
        if value[0] == '"':
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ConditionSyntaxError(
                    "String inválida"
                ) from exc

            if not isinstance(parsed, str):
                raise ConditionSyntaxError(
                    "Literal inválido"
                )

            return parsed

        #
        # String com aspas simples.
        # Mantemos propositalmente uma sintaxe simples:
        # sem escapes especiais.
        #
        content = value[1:-1]

        if "'" in content:
            raise ConditionSyntaxError(
                "String inválida"
            )

        return content

    #
    # Inteiro.
    #
    if re.fullmatch(
        r"-?(0|[1-9]\d*)",
        value,
    ):
        return int(value)

    #
    # Decimal.
    #
    if re.fullmatch(
        r"-?(0|[1-9]\d*)\.\d+",
        value,
    ):
        return float(value)

    raise ConditionSyntaxError(
        "Literal inválido"
    )


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    )


def _equal(
    left: Any,
    right: Any,
) -> bool:
    #
    # bool não deve ser igual a 1/0,
    # apesar do comportamento padrão do Python.
    #
    if _is_number(left) and _is_number(right):
        return left == right

    if type(left) is not type(right):
        return False

    return left == right


def evaluate_condition(
    expression: str,
    variables: dict[str, Any],
) -> bool:
    match = EXPRESSION.fullmatch(
        expression
    )

    if not match:
        raise ConditionSyntaxError(
            "Expressão CONDITION inválida"
        )

    variable_path = match.group(1)
    operator = match.group(2)
    literal_text = match.group(3)

    left = _variable_value(
        variable_path,
        variables,
    )

    right = _literal_value(
        literal_text
    )

    if operator == "==":
        return _equal(
            left,
            right,
        )

    if operator == "!=":
        return not _equal(
            left,
            right,
        )

    #
    # Comparações de ordem:
    # - número com número
    # - string com string
    #
    comparable_numbers = (
        _is_number(left)
        and _is_number(right)
    )

    comparable_strings = (
        isinstance(left, str)
        and isinstance(right, str)
    )

    if not (
        comparable_numbers
        or comparable_strings
    ):
        raise ConditionTypeError(
            "Tipos incompatíveis para comparação"
        )

    if operator == ">":
        return left > right

    if operator == ">=":
        return left >= right

    if operator == "<":
        return left < right

    if operator == "<=":
        return left <= right

    raise ConditionSyntaxError(
        "Operador inválido"
    )
