import hashlib
import hmac
import secrets
import time

from security_config import load_secrets


SESSIONS = {}
SESSION_DURATION = 60 * 60 * 4


def verify_password(password):
    _, stored_hash = load_secrets()

    parts = stored_hash.split("$")

    if len(parts) != 4:
        return False

    algorithm, iterations, salt_hex, hash_hex = parts

    if algorithm != "pbkdf2_sha256":
        return False

    try:
        iterations = int(iterations)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations
    )

    return hmac.compare_digest(
        actual,
        expected
    )


def verify_username(username):
    stored_username, _ = load_secrets()

    return hmac.compare_digest(
        username,
        stored_username
    )


def create_session():
    session_id = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)

    SESSIONS[session_id] = {
        "csrf": csrf_token,
        "created": time.time(),
        "last_seen": time.time()
    }

    return session_id, csrf_token


def get_session(session_id):
    if not session_id:
        return None

    session = SESSIONS.get(session_id)

    if not session:
        return None

    now = time.time()

    if now - session["last_seen"] > SESSION_DURATION:
        SESSIONS.pop(session_id, None)
        return None

    session["last_seen"] = now

    return session


def delete_session(session_id):
    if session_id:
        SESSIONS.pop(session_id, None)
