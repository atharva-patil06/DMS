"""Small string helpers used everywhere in the math core.

We only treat space, tab, CR and LF as whitespace (Python's own strip() and
split() also treat other characters, such as form feeds, as whitespace), so
every input is read exactly the same way as before.
"""

SPACE_CHARS = " \t\r\n"
INT_MIN = -2147483648
INT_MAX = 2147483647


def trim(text):
    """Remove spaces, tabs, CR and LF from both ends of the text."""
    return text.strip(SPACE_CHARS)


def split(text, delimiter):
    """Split on one delimiter character and trim every piece.

    Empty pieces are kept, so callers can report "empty item" errors precisely.
    Example: split("a, b,,c", ",") -> ["a", "b", "", "c"].
    """
    return [trim(piece) for piece in text.split(delimiter)]


def split_whitespace(text):
    """Split on runs of space/tab/CR/LF; empty pieces are dropped."""
    pieces = []
    current = ""
    for char in text:
        if char in SPACE_CHARS:
            if current:
                pieces.append(current)
                current = ""
        else:
            current += char
    if current:
        pieces.append(current)
    return pieces


def is_all_digits(text):
    """True if text is non-empty and every character is an ASCII digit 0-9."""
    if text == "":
        return False
    for char in text:
        if char < "0" or char > "9":
            return False
    return True


def parse_int(text):
    """Strictly read a whole (possibly signed) number, or return None.

    Rejects "", "12a", "1.5" and numbers that do not fit in a 32-bit int,
    exactly like the original C++ version. Leading/trailing spaces are allowed.
    """
    cleaned = trim(text)
    digits = cleaned
    if digits[:1] in ("+", "-"):
        digits = digits[1:]
    if not is_all_digits(digits):
        return None
    value = int(cleaned)
    if value < INT_MIN or value > INT_MAX:
        return None
    return value


def is_valid_label(text):
    """True if text is a valid element label: 1 to 6 characters from [A-Za-z0-9_]."""
    if len(text) == 0 or len(text) > 6:
        return False
    for char in text:
        ok = ("a" <= char <= "z") or ("A" <= char <= "Z") or ("0" <= char <= "9") or char == "_"
        if not ok:
            return False
    return True
