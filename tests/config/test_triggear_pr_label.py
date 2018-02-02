import pytest
from mockito import mock

from app.enums.triggear_pr_label import TriggearPrLabel

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestTriggearPrLabel:
    async def test_equality_with_label(self):
        assert TriggearPrLabel.PR_SYNC != TriggearPrLabel.LABEL_SYNC
        assert TriggearPrLabel.PR_SYNC == TriggearPrLabel.PR_SYNC
        assert TriggearPrLabel.LABEL_SYNC == TriggearPrLabel.LABEL_SYNC

    async def test_equality_with_strings(self):
        assert TriggearPrLabel.LABEL_SYNC == 'triggear-label-sync'
        assert TriggearPrLabel.PR_SYNC == 'triggear-pr-sync'

    async def test_non_equality_with_other_types(self):
        assert TriggearPrLabel.LABEL_SYNC != mock()
        assert TriggearPrLabel.PR_SYNC != mock()
