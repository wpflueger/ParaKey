import re


CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def sanitize_text(text: str) -> str:
    without_controls = CONTROL_PATTERN.sub("", text)
    return without_controls
