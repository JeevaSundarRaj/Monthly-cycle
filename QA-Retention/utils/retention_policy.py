def is_remove_content_only(option_name):
    normalized = option_name.lower()
    if "personally identifiable" in normalized:
        return False
    return "remove content" in normalized
