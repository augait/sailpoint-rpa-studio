"""Isolated fictional legacy application. Never deploy as a real account system."""

import hmac
import os
import secrets
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(docs_url=None, redoc_url=None)
ROOT = Path(__file__).parent
sessions: set[str] = set()
DB = os.getenv("DEMO_DB", "demo.db")


def database():
    db = sqlite3.connect(DB)
    db.execute(
        "CREATE TABLE IF NOT EXISTS accounts (username TEXT PRIMARY KEY, firstname TEXT, lastname TEXT, email TEXT, department TEXT)"
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS entitlements (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS account_entitlements (
            username TEXT NOT NULL,
            entitlement_id TEXT NOT NULL,
            PRIMARY KEY (
                username,
                entitlement_id
            )
        )
        """
    )

    db.executemany(
        """
        INSERT OR IGNORE INTO entitlements (
            id,
            name,
            description
        )
        VALUES (?, ?, ?)
        """,
        [
            (
                "APP_USER",
                "Application User",
                "Basic access to the legacy application",
            ),
            (
                "IT_SUPPORT",
                "IT Support",
                "IT support access",
            ),
            (
                "HR_VIEWER",
                "HR Viewer",
                "Read access to HR resources",
            ),
            (
                "FINANCE_VIEWER",
                "Finance Viewer",
                "Read access to finance resources",
            ),
            (
                "APP_ADMIN",
                "Application Administrator",
                "Administrative access to the legacy application",
            ),
        ],
    )

    db.commit()

    return db


@app.get("/")
def home():
    return FileResponse(ROOT / "index.html")


@app.get("/demo.js")
def script():
    return FileResponse(ROOT / "demo.js", media_type="text/javascript")


@app.post("/session")
async def login(request: Request):
    data = await request.json()
    configured = os.getenv("DEMO_PASSWORD")
    if not configured:
        raise HTTPException(503, "Configure DEMO_PASSWORD")
    if data.get("username") != "demo-admin" or not hmac.compare_digest(
        str(data.get("password", "")), configured
    ):
        raise HTTPException(401, "Invalid login")
    token = secrets.token_urlsafe(32)
    sessions.add(token)
    response = JSONResponse({"ok": True})
    response.set_cookie("demo_session", token, httponly=True, samesite="strict")
    return response


def authenticated(request):
    if request.cookies.get("demo_session") not in sessions:
        raise HTTPException(401)


@app.get("/accounts")
def accounts(request: Request):
    authenticated(request)
    with database() as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute("SELECT * FROM accounts ORDER BY username")]


@app.post("/accounts")
async def create(request: Request):
    authenticated(request)
    data = await request.json()
    keys = ("username", "firstname", "lastname", "email", "department")
    if not all(isinstance(data.get(key), str) and 0 < len(data[key]) <= 200 for key in keys):
        raise HTTPException(422, "Invalid fields")
    with database() as db:
        try:
            db.execute("INSERT INTO accounts VALUES(?,?,?,?,?)", [data[key] for key in keys])
        except sqlite3.IntegrityError:
            return {"message": "User already exists", "accountId": data["username"]}
    return {"message": "User created successfully", "accountId": data["username"]}



@app.put("/accounts/{username}")
async def update_account(
    username: str,
    request: Request,
):
    authenticated(request)

    data = await request.json()

    keys = (
        "firstname",
        "lastname",
        "email",
        "department",
    )

    if not all(
        isinstance(
            data.get(key),
            str,
        )
        and 0 < len(data[key]) <= 200
        for key in keys
    ):
        raise HTTPException(
            422,
            "Invalid fields",
        )

    if data["department"] not in {
        "IT",
        "HR",
        "FINANCE",
    }:
        raise HTTPException(
            422,
            "Invalid department",
        )

    with database() as db:
        existing = db.execute(
            """
            SELECT username
            FROM accounts
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

        if not existing:
            raise HTTPException(
                404,
                "User not found",
            )

        db.execute(
            """
            UPDATE accounts
            SET
                firstname = ?,
                lastname = ?,
                email = ?,
                department = ?
            WHERE username = ?
            """,
            (
                data["firstname"],
                data["lastname"],
                data["email"],
                data["department"],
                username,
            ),
        )

    return {
        "message":
            "User updated successfully",
        "accountId":
            username,
    }



@app.get("/entitlements")
def entitlements(request: Request):
    authenticated(request)

    with database() as db:
        db.row_factory = sqlite3.Row

        return [
            dict(row)
            for row in db.execute(
                """
                SELECT
                    id,
                    name,
                    description
                FROM entitlements
                ORDER BY id
                """
            )
        ]


@app.get("/accounts/{username}/entitlements")
def account_entitlements(
    username: str,
    request: Request,
):
    authenticated(request)

    with database() as db:
        db.row_factory = sqlite3.Row

        account = db.execute(
            """
            SELECT username
            FROM accounts
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

        if not account:
            raise HTTPException(
                404,
                "User not found",
            )

        return [
            dict(row)
            for row in db.execute(
                """
                SELECT
                    e.id,
                    e.name,
                    e.description
                FROM entitlements e
                INNER JOIN account_entitlements ae
                    ON ae.entitlement_id = e.id
                WHERE ae.username = ?
                ORDER BY e.id
                """,
                (username,),
            )
        ]


@app.post(
    "/accounts/{username}/entitlements/{entitlement_id}"
)
def add_entitlement(
    username: str,
    entitlement_id: str,
    request: Request,
):
    authenticated(request)

    with database() as db:
        account = db.execute(
            """
            SELECT username
            FROM accounts
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

        if not account:
            raise HTTPException(
                404,
                "User not found",
            )

        entitlement = db.execute(
            """
            SELECT id
            FROM entitlements
            WHERE id = ?
            """,
            (entitlement_id,),
        ).fetchone()

        if not entitlement:
            raise HTTPException(
                404,
                "Entitlement not found",
            )

        db.execute(
            """
            INSERT OR IGNORE INTO account_entitlements (
                username,
                entitlement_id
            )
            VALUES (?, ?)
            """,
            (
                username,
                entitlement_id,
            ),
        )

    return {
        "message":
            "Entitlement added successfully",
        "username":
            username,
        "entitlementId":
            entitlement_id,
    }


@app.delete(
    "/accounts/{username}/entitlements/{entitlement_id}"
)
def remove_entitlement(
    username: str,
    entitlement_id: str,
    request: Request,
):
    authenticated(request)

    with database() as db:
        db.execute(
            """
            DELETE FROM account_entitlements
            WHERE
                username = ?
                AND entitlement_id = ?
            """,
            (
                username,
                entitlement_id,
            ),
        )

    return {
        "message":
            "Entitlement removed successfully",
        "username":
            username,
        "entitlementId":
            entitlement_id,
    }
