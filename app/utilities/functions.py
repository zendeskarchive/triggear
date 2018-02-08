from typing import List, Any, Set, Optional


def starts_with_item_from_list(string: str, list_of_strings: List[str]) -> bool:
    return any([string.startswith(restriction) for restriction in list_of_strings])


def string_if_starts_with_item_from_list(string: str, set_of_strings: Set[str]) -> Optional[str]:
    for item in set_of_strings:
        if string.startswith(item):
            return string
    return None


def any_starts_with(any_list: Set[str], starts_with_list: List[str]) -> bool:
    return any([starts_with_item_from_list(change, starts_with_list) for change in any_list])


def flatten_list(list_of_lists: List[List[Any]]) -> List[Any]:
    return [item for sublist in list_of_lists for item in sublist]


def get_all_starting_with(strings_list: Set[str], prefixes_list: List[str]) -> Set[str]:
    return {string for string in strings_list if starts_with_item_from_list(string, prefixes_list)}
