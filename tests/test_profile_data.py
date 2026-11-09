import unittest

from src.loader import Document
from src.profile_data import duplicate_metrics, extract_body, normalize_text


class ProfileDataTests(unittest.TestCase):
    def test_minimal_text_normalization(self):
        self.assertEqual(normalize_text("HOLA\r\n  Mundo!"), "hola mundo!")

    def test_removes_header_block_only_when_it_looks_like_headers(self):
        message = "From: person@example.com\nSubject: Test\n\nMessage body"
        self.assertEqual(extract_body(message), "Message body")
        self.assertEqual(extract_body("Text\n\nMore text"), "Text\n\nMore text")

    def test_duplicate_pair_and_cross_category_counts(self):
        docs = [
            Document("a", "all", "group.one", "same", "a"),
            Document("b", "all", "group.two", "same", "b"),
            Document("c", "all", "group.one", "same", "c"),
        ]
        metrics = duplicate_metrics(docs, lambda text: text)
        self.assertEqual(metrics["duplicate_groups"], 1)
        self.assertEqual(metrics["duplicate_documents_beyond_first"], 2)
        self.assertEqual(metrics["duplicate_pairs"], 3)
        self.assertEqual(metrics["groups_spanning_categories"], 1)
        self.assertEqual(metrics["cross_category_duplicate_pairs"], 2)


if __name__ == "__main__":
    unittest.main()
