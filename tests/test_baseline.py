import csv
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from src.baseline import brute_force_pairs, run_exact_baseline
from src.loader import Document


class ExactBaselineTests(unittest.TestCase):
    def test_inverted_index_matches_brute_force_on_small_corpus(self):
        documents = [
            Document("doc-a", "all", "group.a", "alpha beta gamma delta epsilon zeta", "a"),
            Document("doc-b", "all", "group.b", "alpha beta gamma delta theta zeta", "b"),
            Document("doc-c", "all", "group.c", "one two three four five six", "c"),
        ]
        thresholds = [Fraction(2, 5), Fraction(1, 2)]
        expected = brute_force_pairs(documents, k=2, thresholds=thresholds)

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            summary = run_exact_baseline(
                documents.copy(),
                version="original",
                k=2,
                thresholds=thresholds,
                output_dir=output_dir,
                batch_size=2,
            )

            result_path = output_dir / "pairs_original_k2_t0p4.csv"
            with result_path.open(newline="", encoding="utf-8") as source:
                rows = list(csv.DictReader(source))
            found = {(row["doc_a"], row["doc_b"]) for row in rows}

        self.assertEqual(found, expected[Fraction(2, 5)])
        self.assertEqual(summary["documents"], 3)
        self.assertEqual(summary["all_document_pairs"], 3)
        self.assertEqual(summary["exact_pairs_by_threshold"], {"0.4": 1, "0.5": 0})


if __name__ == "__main__":
    unittest.main()
