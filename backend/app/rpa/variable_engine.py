import re
from typing import Any

PATTERN = re.compile(r"{{\s*([A-Za-z_][\w.]*)\s*}}")


def resolve(text: str, variables: dict[str, Any]) -> str:
    def replace(match):
        value: Any = variables
        for part in match.group(1).split("."):
            if not isinstance(value, dict) or part not in value:
                raise ValueError(f"Variável ausente: {match.group(1)}")
            value = value[part]
        if isinstance(value, (dict, list)) or value is None:
            raise ValueError("Variável deve ser escalar")
        return str(value)

    return PATTERN.sub(replace, text)
