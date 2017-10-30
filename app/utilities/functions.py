def starts_with_item_from_list(string, list_of_strings):
    return any([string.startswith(restriction) for restriction in list_of_strings])


def any_starts_with(any_list, starts_with_list):
    return any([starts_with_item_from_list(change, starts_with_list) for change in any_list])


def flatten_list(list_of_lists):
    return [item for sublist in list_of_lists for item in sublist]
