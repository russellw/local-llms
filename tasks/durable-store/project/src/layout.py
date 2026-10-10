"""How keys map to file names. See docs/design.md."""

PREFIX = "d."


def data_name(key):
    """The file holding `key`'s value."""
    return PREFIX + key


def key_of(name):
    """The key a data file holds, or None if `name` is not a data file."""
    if not name.startswith(PREFIX):
        return None
    return name[len(PREFIX):]
