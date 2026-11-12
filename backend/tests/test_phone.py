import pytest

from app.services.phone import last4_spoken, spoken_phone, to_e164


@pytest.mark.parametrize("digits, expected", [
    ("3125550120", "+13125550120"),       # US 10-digit
    ("940701465245", "+940701465245"),    # includes a country code
    ("5550120", None),                    # regression: 7-digit local numbers aren't dialable
    ("1234567890123456", None),           # too long for E.164
])
def test_to_e164(digits, expected):
    assert to_e164(digits) == expected


def test_spoken_forms():
    assert spoken_phone("3125550120") == "312 555 0120"
    assert last4_spoken("3125550120") == "0 1 2 0"
