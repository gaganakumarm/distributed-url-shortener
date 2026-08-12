from app.services.shortcodes import generate_short_code


def test_short_code_length():
    code = generate_short_code(8)
    assert len(code) == 8


def test_short_codes_are_different():
    assert generate_short_code(8) != generate_short_code(8)
