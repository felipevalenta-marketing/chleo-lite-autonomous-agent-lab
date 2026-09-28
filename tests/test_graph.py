from __future__ import annotations

import unittest


@unittest.skip("LangGraph tests are deferred until the workflow implementation phase.")
class TestGraphPlaceholder(unittest.TestCase):
    def test_placeholder(self) -> None:
        self.fail("This placeholder test should remain skipped.")
