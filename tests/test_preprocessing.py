import unittest

from src.preprocessing import normalize_text, preprocess_to_tokens
from src.shingling import word_shingles


class PreprocessingTests(unittest.TestCase):
    def test_normalizes_unicode_case_and_whitespace(self):
        self.assertEqual(normalize_text("ＡBC\r\n  DEF"), "abc def")

    def test_removes_header_and_signature_but_keeps_quoted_content(self):
        message = (
            "From: sender@example.com\n"
            "Subject: A Test\n"
            "Organization: Example\n"
            "\n"
            "Quoted: > KEEP THIS TEXT\n"
            "Body words here\n"
            "-- \n"
            "Signature words removed\n"
        )
        tokens = preprocess_to_tokens(message)
        self.assertIn("quoted", tokens)
        self.assertIn("keep", tokens)
        self.assertIn("body", tokens)
        self.assertNotIn("sender", tokens)
        self.assertNotIn("subject", tokens)
        self.assertNotIn("signature", tokens)

    def test_word_tokenizer_and_five_word_shingles(self):
        tokens = preprocess_to_tokens("El presidente anunció un plan económico.")
        self.assertEqual(tokens, ["el", "presidente", "anunció", "un", "plan", "económico"])
        self.assertEqual(
            word_shingles(tokens, 5),
            {
                ("el", "presidente", "anunció", "un", "plan"),
                ("presidente", "anunció", "un", "plan", "económico"),
            },
        )

    def test_short_text_has_no_shingles_and_invalid_k_fails(self):
        self.assertEqual(word_shingles(["only", "four", "words", "here"], 5), set())
        with self.assertRaises(ValueError):
            word_shingles(["one"], 0)


if __name__ == "__main__":
    unittest.main()
