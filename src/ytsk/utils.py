import re


def sanitize_title(title: str) -> str:
    """Replace spaces with underscores and remove special characters."""
    s = title.replace(" ", "_")
    s = re.sub(r"[^a-zA-Z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "untitled"
