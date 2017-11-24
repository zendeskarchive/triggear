from typing import List, Any, Set


def starts_with_item_from_list(string: str, list_of_strings: List[str]) -> bool:
    return any([string.startswith(restriction) for restriction in list_of_strings])


def any_starts_with(any_list: Set[str], starts_with_list: List[str]) -> bool:
    return any([starts_with_item_from_list(change, starts_with_list) for change in any_list])


def flatten_list(list_of_lists: List[List[Any]]) -> List[Any]:
    return [item for sublist in list_of_lists for item in sublist]
