"""Prepare local secrets without replacing existing project configuration."""
import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
env_path = ROOT / ".env"
content = env_path.read_text(encoding="utf-8-sig") if env_path.exists() else ""
defaults = {
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "15432",
    "POSTGRES_DB": "RAG_agent",
    "POSTGRES_USER": "rag_user",
    "POSTGRES_PASSWORD": secrets.token_hex(24),
    "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
    "DJANGO_DEBUG": "True",
    "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,[::1]",
}
changed = False
for key, value in defaults.items():
    pattern = rf"(?m)^{re.escape(key)}\s*=([^\r\n]*)"
    match = re.search(pattern, content)
    if match is None:
        content = content.rstrip("\r\n") + f"\n{key}={value}\n"
        changed = True
    elif not match.group(1).strip().strip("\"'"):
        content = re.sub(pattern, lambda _: f"{key}={value}", content, count=1)
        changed = True
if changed:
    env_path.write_text(content, encoding="utf-8")
print("Configuration locale prête (.env). Les valeurs existantes sont conservées.")
