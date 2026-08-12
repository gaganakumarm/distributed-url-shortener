import secrets
import string

ALPHABET = string.ascii_letters + string.digits


def generate_short_code(length: int = 8) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
