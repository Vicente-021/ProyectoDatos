"""Baseline exacto de Jaccard usando un índice invertido de shingles.

Para cualquier umbral positivo, dos documentos sin shingles en común tienen
Jaccard cero y no pueden pertenecer a la respuesta. El índice cuenta todas las
intersecciones no vacías; la decisión final usa la intersección y unión exactas.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import sqlite3
import tempfile
import time
from array import array
from collections import defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from typing import Iterable

if __package__:
    from .loader import DATASETS, Document, load_20newsgroups
    from .preprocessing import preprocess_to_tokens
    from .shingling import word_shingles
else:  # allows: python3 src/baseline.py
    from loader import DATASETS, Document, load_20newsgroups
    from preprocessing import preprocess_to_tokens
    from shingling import word_shingles


DEFAULT_THRESHOLDS = ("0.5", "0.7", "0.9")
PAIR_UPSERT = """
INSERT INTO overlaps(doc_a, doc_b, shared) VALUES (?, ?, 1)
ON CONFLICT(doc_a, doc_b) DO UPDATE SET shared = shared + 1
"""


def parse_thresholds(values: Iterable[str | Fraction]) -> list[Fraction]:
    thresholds = [value if isinstance(value, Fraction) else Fraction(str(value)) for value in values]
    if not thresholds:
        raise ValueError("Se requiere al menos un umbral")
    if any(value <= 0 or value > 1 for value in thresholds):
        raise ValueError("Los umbrales deben estar en el intervalo (0, 1]")
    if len(set(thresholds)) != len(thresholds):
        raise ValueError("Los umbrales deben ser únicos")
    return thresholds


def _threshold_label(threshold: Fraction) -> str:
    return f"{float(threshold):g}"


def _add_posting(postings: dict, shingle: tuple[str, ...], doc_id: int) -> None:
    current = postings.get(shingle)
    if current is None:
        postings[shingle] = doc_id
    elif isinstance(current, int):
        postings[shingle] = array("I", (current, doc_id))
    else:
        current.append(doc_id)


def run_exact_baseline(
    documents: list[Document],
    *,
    version: str,
    k: int = 5,
    thresholds: Iterable[str | Fraction] = DEFAULT_THRESHOLDS,
    output_dir: Path,
    batch_size: int = 50_000,
) -> dict:
    """Produce exact threshold pair files and a compact run summary.

    Pair intersection counters are accumulated in a temporary SQLite database
    to avoid keeping a potentially large pair dictionary in Python memory.
    Only document pairs sharing at least one shingle are enumerated.
    """
    if version not in DATASETS:
        raise ValueError(f"Versión desconocida: {version}")
    if k < 1:
        raise ValueError("k debe ser al menos 1")
    if batch_size < 1:
        raise ValueError("batch_size debe ser positivo")
    thresholds = parse_thresholds(thresholds)
    output_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    metadata: list[tuple[str, str]] = []
    doc_sizes: list[int] = []
    postings: dict[tuple[str, ...], int | array] = {}
    shingle_occurrences = 0

    for doc_index, document in enumerate(documents):
        metadata.append((document.doc_id, document.category))
        shingles = word_shingles(preprocess_to_tokens(document.text), k=k)
        doc_sizes.append(len(shingles))
        shingle_occurrences += len(shingles)
        for shingle in shingles:
            _add_posting(postings, shingle, doc_index)

    index_built_at = time.perf_counter()
    total_docs = len(documents)
    total_pairs = total_docs * (total_docs - 1) // 2
    distinct_shingles = len(postings)
    shared_pair_incidences = sum(
        len(posting) * (len(posting) - 1) // 2
        for posting in postings.values()
        if not isinstance(posting, int)
    )
    del documents
    gc.collect()

    labels = {_threshold_label(value): value for value in thresholds}
    output_paths = {
        label: output_dir / f"pairs_{version}_k{k}_t{label.replace('.', 'p')}.csv"
        for label in labels
    }
    pair_counts = {label: 0 for label in labels}
    output_files = {label: path.open("w", newline="", encoding="utf-8") for label, path in output_paths.items()}
    writers = {
        label: csv.writer(stream, lineterminator="\n")
        for label, stream in output_files.items()
    }
    for writer in writers.values():
        writer.writerow(("doc_a", "category_a", "doc_b", "category_b", "intersection", "union", "jaccard"))

    try:
        with tempfile.TemporaryDirectory(prefix="20news-baseline-") as temp_dir:
            database_path = Path(temp_dir) / "intersections.sqlite3"
            connection = sqlite3.connect(database_path)
            connection.execute("PRAGMA journal_mode = OFF")
            connection.execute("PRAGMA synchronous = OFF")
            connection.execute("PRAGMA temp_store = MEMORY")
            connection.execute(
                "CREATE TABLE overlaps (doc_a INTEGER, doc_b INTEGER, shared INTEGER, "
                "PRIMARY KEY (doc_a, doc_b)) WITHOUT ROWID"
            )

            batch: list[tuple[int, int]] = []
            for posting in postings.values():
                if isinstance(posting, int):
                    continue
                for doc_a, doc_b in combinations(posting, 2):
                    batch.append((doc_a, doc_b))
                    if len(batch) >= batch_size:
                        connection.executemany(PAIR_UPSERT, batch)
                        connection.commit()
                        batch.clear()
            if batch:
                connection.executemany(PAIR_UPSERT, batch)
                connection.commit()
                batch.clear()

            del postings
            gc.collect()
            shared_pairs = connection.execute("SELECT COUNT(*) FROM overlaps").fetchone()[0]

            cursor = connection.execute(
                "SELECT doc_a, doc_b, shared FROM overlaps ORDER BY doc_a, doc_b"
            )
            for doc_a, doc_b, shared in cursor:
                union = doc_sizes[doc_a] + doc_sizes[doc_b] - shared
                # Empty shingle sets have no posting and therefore cannot be
                # selected here. Keep the guard for defensive correctness.
                if union <= 0:
                    continue
                doc_id_a, category_a = metadata[doc_a]
                doc_id_b, category_b = metadata[doc_b]
                for label, threshold in labels.items():
                    if shared * threshold.denominator >= threshold.numerator * union:
                        pair_counts[label] += 1
                        writers[label].writerow(
                            (
                                doc_id_a,
                                category_a,
                                doc_id_b,
                                category_b,
                                shared,
                                union,
                                f"{shared / union:.12g}",
                            )
                        )
            connection.close()
    finally:
        for stream in output_files.values():
            stream.close()

    finished = time.perf_counter()
    summary = {
        "version": version,
        "k_words": k,
        "thresholds": {label: f"{value.numerator}/{value.denominator}" for label, value in labels.items()},
        "documents": total_docs,
        "all_document_pairs": total_pairs,
        "documents_with_zero_shingles": sum(size == 0 for size in doc_sizes),
        "distinct_shingles": distinct_shingles,
        "shingle_occurrences_across_documents": shingle_occurrences,
        "shared_pair_incidences": shared_pair_incidences,
        "pairs_sharing_at_least_one_shingle": shared_pairs,
        "exact_pairs_by_threshold": pair_counts,
        "csv_files": {label: str(path) for label, path in output_paths.items()},
        "index_build_seconds": round(index_built_at - started, 3),
        "total_seconds": round(finished - started, 3),
        "method": (
            "Exact inverted-index enumeration: every pair with positive Jaccard shares a shingle; "
            "all other pairs have Jaccard zero and cannot meet a positive threshold."
        ),
    }
    summary_path = output_dir / f"baseline_{version}_k{k}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def brute_force_pairs(
    documents: list[Document], k: int, thresholds: Iterable[str | Fraction]
) -> dict[Fraction, set[tuple[str, str]]]:
    """Small-data reference implementation that checks every document pair."""
    from itertools import combinations as pair_combinations

    thresholds = parse_thresholds(thresholds)
    shingles = [
        word_shingles(preprocess_to_tokens(document.text), k=k)
        for document in documents
    ]
    results = {threshold: set() for threshold in thresholds}
    for index_a, index_b in pair_combinations(range(len(documents)), 2):
        set_a, set_b = shingles[index_a], shingles[index_b]
        intersection = len(set_a & set_b)
        union = len(set_a) + len(set_b) - intersection
        if union == 0:
            continue
        doc_pair = (documents[index_a].doc_id, documents[index_b].doc_id)
        for threshold in thresholds:
            if intersection * threshold.denominator >= threshold.numerator * union:
                results[threshold].add(doc_pair)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "baselines")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--thresholds", nargs="+", default=list(DEFAULT_THRESHOLDS))
    parser.add_argument("--version", choices=(*DATASETS, "both"), default="both")
    parser.add_argument("--batch-size", type=int, default=50_000)
    args = parser.parse_args()
    if args.k < 1:
        parser.error("--k debe ser al menos 1")
    try:
        thresholds = parse_thresholds(args.thresholds)
    except (ValueError, ZeroDivisionError) as error:
        parser.error(str(error))

    versions = DATASETS if args.version == "both" else (args.version,)
    for version in versions:
        print(f"\n=== Baseline exacto: {version} ===", flush=True)
        documents = load_20newsgroups(args.data_dir, version)
        summary = run_exact_baseline(
            documents,
            version=version,
            k=args.k,
            thresholds=thresholds,
            output_dir=args.output_dir,
            batch_size=args.batch_size,
        )
        print(f"Documentos: {summary['documents']:,}")
        print(f"Pares totales posibles: {summary['all_document_pairs']:,}")
        print(f"Pares con shingles compartidos: {summary['pairs_sharing_at_least_one_shingle']:,}")
        print(f"Incidencias de pares desde postings: {summary['shared_pair_incidences']:,}")
        print(f"Pares exactos por umbral: {summary['exact_pairs_by_threshold']}")
        print(f"Tiempo total: {summary['total_seconds']} s")
        print(f"Resumen: {args.output_dir / f'baseline_{version}_k{args.k}.json'}")
        del documents


if __name__ == "__main__":
    main()
