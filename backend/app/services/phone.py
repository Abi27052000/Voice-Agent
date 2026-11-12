"""Phone helpers. Numbers are stored as digits only (see schemas/tools.normalize_phone)."""


def spoken_phone(digits: str) -> str:
    """Group digits so a voice reads them naturally: '3125550120' -> '312 555 0120'."""
    if len(digits) == 10:
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
    return " ".join(digits[i : i + 3] for i in range(0, len(digits), 3))


def last4_spoken(digits: str) -> str:
    return " ".join(digits[-4:])


def to_e164(digits: str) -> str | None:
    """US 10-digit -> +1XXXXXXXXXX; 11-15 digits are assumed to include a country code.

    Returns None for numbers too short to dial (e.g. 7-digit local numbers), so
    callers can exclude them instead of sending an invalid number to Vapi.
    """
    if len(digits) == 10:
        return f"+1{digits}"
    if 11 <= len(digits) <= 15:
        return f"+{digits}"
    return None
