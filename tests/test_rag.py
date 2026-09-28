from __future__ import annotations

import unittest


@unittest.skip("RAG tests are deferred until the retrieval implementation phase.")
class TestRagPlaceholder(unittest.TestCase):
    def test_placeholder(self) -> None:
        self.fail("This placeholder test should remain skipped.")
