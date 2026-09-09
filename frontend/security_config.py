from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SECRETS_FILE = BASE_DIR / "secrets.env"


def load_secrets():
    if not SECRETS_FILE.exists():
        raise RuntimeError("secrets.env bulunamadı.")

    secrets = {}

    for line in SECRETS_FILE.read_text(
        encoding="utf-8"
    ).splitlines():

        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        secrets[key.strip()] = value.strip()

    username = secrets.get("ADMIN_USERNAME")
    password_hash = secrets.get("ADMIN_PASSWORD_HASH")

    if not username or not password_hash:
        raise RuntimeError(
            "Admin güvenlik bilgileri eksik."
        )

    return username, password_hash
