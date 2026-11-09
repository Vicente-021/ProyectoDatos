import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from src.loader import load_documents


class LoadDocumentsTests(unittest.TestCase):
    def test_reads_text_category_split_and_stable_ids(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = Path(temporary_directory) / "sample.tar.gz"
            files = {
                "20news-bydate-train/comp.graphics/001": b"Train message\n",
                "20news-bydate-test/comp.graphics/002": b"Test message\n",
                "other-folder/ignored/file": b"Ignore me\n",
            }

            with tarfile.open(archive_path, mode="w:gz") as archive:
                for name, content in files.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    archive.addfile(info, io.BytesIO(content))

            documents = load_documents(archive_path)

        self.assertEqual(len(documents), 2)
        self.assertEqual(documents[0].doc_id, "test/comp.graphics/002")
        self.assertEqual(documents[0].split, "test")
        self.assertEqual(documents[0].category, "comp.graphics")
        self.assertEqual(documents[0].text, "Test message\n")
        self.assertEqual(documents[1].doc_id, "train/comp.graphics/001")
        self.assertEqual(documents[1].text, "Train message\n")

    def test_reads_original_archive_layout(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = Path(temporary_directory) / "original.tar.gz"
            content = b"Original message\n"
            with tarfile.open(archive_path, mode="w:gz") as archive:
                info = tarfile.TarInfo("20_newsgroups/alt.atheism/12345")
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))

            documents = load_documents(archive_path, version="original")

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].doc_id, "all/alt.atheism/12345")
        self.assertEqual(documents[0].split, "all")
        self.assertEqual(documents[0].text, "Original message\n")


if __name__ == "__main__":
    unittest.main()
