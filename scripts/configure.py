import secrets
from pathlib import Path

from cryptography.fernet import Fernet

path = Path(".env")
if path.exists():
    raise SystemExit(".env already exists; it was not overwritten")
password = secrets.token_hex(24)
content = Path(".env.example").read_text().replace("CHANGE_ME", password)
content = content.replace("JWT_SECRET=\n", "JWT_SECRET=" + secrets.token_urlsafe(48) + "\n")
content = content.replace(
    "ENCRYPTION_KEY=\n", "ENCRYPTION_KEY=" + Fernet.generate_key().decode() + "\n"
)
path.write_text(content)
path.chmod(0o600)
print(".env created with unique secrets. Do not commit or share it.")
