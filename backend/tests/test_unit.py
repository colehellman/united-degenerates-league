# backend/tests/test_unit.py
import pytest

from app.core.config import Settings


@pytest.mark.unit
def test_cors_origins_list_parsing():
    """
    Test the parsing of the CORS_ORIGINS string into a list.
    This is a pure unit test that doesn't require any external services.
    """
    # Test with a single origin
    settings = Settings(CORS_ORIGINS="http://localhost:3000")
    assert settings.cors_origins_list == ["http://localhost:3000"]

    # Test with multiple origins, with whitespace
    settings = Settings(
        CORS_ORIGINS=" http://localhost:3000, https://udl.app ,http://127.0.0.1:5173 "
    )
    assert settings.cors_origins_list == [
        "http://localhost:3000",
        "https://udl.app",
        "http://127.0.0.1:5173",
    ]

    # Test with an empty string
    settings = Settings(CORS_ORIGINS="")
    assert settings.cors_origins_list == []

    # Test with only whitespace and commas
    settings = Settings(CORS_ORIGINS=" , , ")
    assert settings.cors_origins_list == []


@pytest.mark.unit
def test_production_rejects_default_secret_key():
    """check_production_secrets raises when production still has the dev SECRET_KEY (lines 38-42).

    Init kwargs take priority over env vars in pydantic-settings v2, so this
    instantiation uses the values we pass rather than any CI environment variable.
    DATABASE_URL is set to a safe value so only the first branch fires.
    """
    with pytest.raises(ValueError, match="SECRET_KEY must be changed"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="dev-secret-key-change-in-production",
            DATABASE_URL="postgresql://user:securepass@host/db",
        )


@pytest.mark.unit
def test_production_rejects_default_db_password():
    """check_production_secrets raises when DATABASE_URL contains the dev password (lines 43-47)."""
    with pytest.raises(ValueError, match="DATABASE_URL still contains"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a-safe-unique-production-secret-key",
            DATABASE_URL="postgresql://user:udl_password@host/db",
        )
