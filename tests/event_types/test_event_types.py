from app.event_types import EventTypes


def test_types_are_as_in_hooks():
    assert EventTypes.comment == "created"
    assert EventTypes.push == "push"
    assert EventTypes.labeled == "labeled"
    assert EventTypes.synchronize == "synchronize"
    assert EventTypes.pull_request == "pull_request"
    assert EventTypes.pr_opened == "opened"
    assert EventTypes.tagged == "tagged"
