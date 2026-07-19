import unittest

from core.research import WebResearcher


class ResearchSafetyTests(unittest.TestCase):
    def test_rejects_local_and_credentialed_urls(self) -> None:
        self.assertFalse(WebResearcher._is_public_http_url("http://127.0.0.1/admin"))
        self.assertFalse(WebResearcher._is_public_http_url("http://user:pass@example.com"))
        self.assertFalse(WebResearcher._is_public_http_url("file:///etc/passwd"))

    def test_rejects_missing_and_invalid_citations(self) -> None:
        self.assertIn("won't present", WebResearcher._validate_citations("A factual answer.", 2))
        self.assertIn("invalid", WebResearcher._validate_citations("Claim [3]", 2))

    def test_accepts_valid_citations(self) -> None:
        self.assertEqual(WebResearcher._validate_citations("Verified claim [1][2]", 2), "Verified claim [1][2]")


if __name__ == "__main__":
    unittest.main()
