from typing import List, Set, Optional

import pytest

from app.utilities.functions import flatten_list, any_starts_with, starts_with_item_from_list, get_all_starting_with, string_if_starts_with_item_from_list


def test__flatten_list():
    assert flatten_list([['a', 'b'], [1], [{2: 3}]]) == ['a', 'b', 1, {2: 3}]


@pytest.mark.parametrize("collection, list_of_prefixes, expected_result", [
    ({'true', 'false'}, ['tr', 'fa'], True),
    ({'true', 'false'}, ['fa'], True),
    ({'true', 'false'}, ['bad'], False)
])
def test__any_starts_with(collection: Set[str], list_of_prefixes: List[str], expected_result: bool):
    assert any_starts_with(collection, list_of_prefixes) == expected_result


@pytest.mark.parametrize("string, list_of_prefixes, expected_result", [
    ('true', ['tr', 'fa'], True),
    ('false', ['fa'], True),
    ('true', ['bad', 'fa'], False)
])
def test__starts_with_item_from_list(string: str, list_of_prefixes: List[str], expected_result: bool):
    assert starts_with_item_from_list(string, list_of_prefixes) == expected_result


@pytest.mark.parametrize("collection, list_of_prefixes, expected_result", [
    ({'true', 'false'}, ['tr', 'fa'], {'true', 'false'}),
    ({'true', 'false'}, ['fa'], {'false'}),
    ({'true', 'false'}, ['bad'], set())
])
def test__get_all_starting_with(collection: Set[str], list_of_prefixes: List[str], expected_result: bool):
    assert get_all_starting_with(collection, list_of_prefixes) == expected_result


@pytest.mark.parametrize("collection, string, expected_result", [
    ({'tr', 'fa'}, 'true', 'true'),
    ({'tr', 'fa'}, 'false', 'false'),
    ({'true', 'false'}, 'bad', None),
    ({'true', 'false'}, 'fals', None),
    ({}, 'true', None)
])
def test__string_if_starts_with_item_from_list(collection: Set[str], string: str, expected_result: Optional[str]):
    assert string_if_starts_with_item_from_list(string, collection) == expected_result
