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
