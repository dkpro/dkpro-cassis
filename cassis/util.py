def is_file_like(obj) -> bool:
    if not (hasattr(obj, "read") or hasattr(obj, "write")):
        return False

    if not hasattr(obj, "__iter__"):
        return False

    return True
