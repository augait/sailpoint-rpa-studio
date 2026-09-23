import argparse
import getpass

from sqlalchemy import select

from backend.app.core.database import Session
from backend.app.core.security import hasher
from backend.app.models.entities import User

parser = argparse.ArgumentParser(
    description="Create a Studio user; password is never a CLI argument"
)
parser.add_argument("username")
parser.add_argument("--role", choices=["ADMIN", "DEVELOPER", "OPERATOR", "VIEWER"], default="ADMIN")
args = parser.parse_args()
password = getpass.getpass("Password (minimum 12 characters): ")
if len(password) < 12:
    raise SystemExit("Use at least 12 characters")
if password != getpass.getpass("Confirm password: "):
    raise SystemExit("Passwords do not match")
with Session() as db:
    if db.scalar(select(User).where(User.username == args.username)):
        raise SystemExit("User already exists")
    db.add(User(username=args.username, password_hash=hasher.hash(password), role=args.role))
    db.commit()
print("User created")
