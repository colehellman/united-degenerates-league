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
    settings = Settings(CORS_ORIGINS=" http://localhost:3000, https://udl.app ,http://127.0.0.1:5173 ")
    assert settings.cors_origins_list == ["http://localhost:3000", "https://udl.app", "http://127.0.0.1:5173"]

    # Test with an empty string
    settings = Settings(CORS_ORIGINS="")
    assert settings.cors_origins_list == []
    
    # Test with only whitespace and commas
    settings = Settings(CORS_ORIGINS=" , , ")
    assert settings.cors_origins_list == []
