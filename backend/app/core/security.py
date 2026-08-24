"""
Security helpers for headers, input sanitation, and future token verification.
"""
import html


def sanitize_input(text: str) -> str:
    """Sanitize user input string."""
    if not text:
        return ""
    # Strip dangerous characters or raw HTML escaping where applicable
    return html.escape(text.strip())
