import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

from app.api.deps import get_current_user
from app.core.config import Settings
from app.core.security import ALGORITHM, create_access_token, decode_access_token
from app.core.config import settings
from jose import jwt


def test_access_token_round_trip():
    token = create_access_token("123")
    assert decode_access_token(token) == "123"


def test_invalid_access_token_returns_none():
    assert decode_access_token("not-a-token") is None


def test_production_rejects_default_secret():
    with pytest.raises(ValidationError):
        Settings(environment="production", secret_key="change-me")


def test_shortcode_length_must_fit_database_column():
    with pytest.raises(ValidationError):
        Settings(short_code_length=33)


@pytest.mark.asyncio
async def test_non_numeric_token_subject_returns_401():
    token = jwt.encode({"sub": "not-a-user-id"}, settings.secret_key, algorithm=ALGORITHM)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as error:
        await get_current_user(credentials=credentials, db=None)

    assert error.value.status_code == 401
