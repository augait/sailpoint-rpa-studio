import argparse
import getpass
import json
from pathlib import Path

import httpx


def template():
    def step(kind, name, selector=None, **extra):
        return {
            "id": f"step-{name.lower().replace(' ', '-')}",
            "type": kind,
            "name": name,
            "selectors": [{"kind": "css", "value": selector}] if selector else [],
            **extra,
        }

    return {
        "name": "CREATE_ACCOUNT · Legacy IAM Portal",
        "operation": "CREATE_ACCOUNT",
        "steps": [
            step("navigate", "Open portal", url="{{application.url}}"),
            step("fill", "Admin username", "#login-username", value="{{admin_username}}"),
            step(
                "fill", "Admin password", "#login-password", value="{{admin_password}}", secret=True
            ),
            step("click", "Login", "#login"),
            step("click", "Users", "#users"),
            step("click", "New user", "#new-user"),
            step("fill", "Username", "#username", value="{{username}}"),
            step("fill", "First name", "#firstname", value="{{firstname}}"),
            step("fill", "Last name", "#lastname", value="{{lastname}}"),
            step("fill", "Email", "#email", value="{{email}}"),
            step("select", "Department", "#department", value="{{department}}"),
            step("click", "Save", "#save"),
            step("assert_text", "Validate success", "#result", value="User created successfully"),
            step("extract_text", "Return account", "#account-id", output="accountId"),
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8080")
    parser.add_argument("--legacy-url", default="http://legacy:8081")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    if args.export:
        Path("demo/workflow.json").write_text(json.dumps(template(), indent=2, ensure_ascii=False))
    else:
        with httpx.Client(base_url=args.api, timeout=30) as client:
            r = client.post(
                "/api/v1/auth/login",
                json={"username": args.username, "password": getpass.getpass("Studio password: ")},
            )
            r.raise_for_status()
            client.headers["Authorization"] = "Bearer " + r.json()["access_token"]
            r = client.post(
                "/api/v1/applications", json={"name": "Legacy IAM Portal", "url": args.legacy_url}
            )
            r.raise_for_status()
            body = {**template(), "application_id": r.json()["id"]}
            r = client.post("/api/v1/workflows", json=body)
            r.raise_for_status()
            print("Workflow created:", r.json()["id"])
