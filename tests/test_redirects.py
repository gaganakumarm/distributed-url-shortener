from app.api.redirects import truncate_header


def test_truncate_header_limits_database_value():
    assert truncate_header("x" * 600) == "x" * 512


def test_truncate_header_preserves_missing_value():
    assert truncate_header(None) is None
