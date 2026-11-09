"""Perfila ambas versiones de 20 Newsgroups antes del preprocesamiento."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

if __package__:
    from .loader import DATASETS, Document, load_20newsgroups
else:  # permite ejecutar directamente: python3 src/profile_data.py
    from loader import DATASETS, Document, load_20newsgroups


HEADER_FIELD = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*:\s*")


def normalize_text(text: str) -> str:
    """Normalización mínima para comparar duplicados, no es el preprocesamiento final."""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return " ".join(text.split())


def extract_body(text: str) -> str:
    """Quita el bloque inicial de cabeceras solo si tiene forma de encabezado."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    header, separator, body = text.partition("\n\n")
    if not separator:
        return text
    header_lines = header.splitlines()
    if any(HEADER_FIELD.match(line) for line in header_lines):
        return body
    return text


def percentile(values: list[int], q: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, int(q * len(ordered) + 0.999999) - 1))]


def duplicate_metrics(documents: list[Document], key_builder) -> dict[str, int]:
    groups: dict[bytes, Counter[str]] = defaultdict(Counter)
    for document in documents:
        key = key_builder(document.text)
        if not key.strip():
            continue
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        groups[digest][document.category] += 1

    duplicate_groups = [counts for counts in groups.values() if sum(counts.values()) > 1]
    duplicate_documents = sum(sum(counts.values()) - 1 for counts in duplicate_groups)
    duplicate_pairs = sum(
        sum(counts.values()) * (sum(counts.values()) - 1) // 2
        for counts in duplicate_groups
    )
    cross_category_groups = sum(len(counts) > 1 for counts in duplicate_groups)
    cross_category_pairs = sum(
        sum(counts.values()) * (sum(counts.values()) - 1) // 2
        - sum(count * (count - 1) // 2 for count in counts.values())
        for counts in duplicate_groups
    )
    return {
        "duplicate_groups": len(duplicate_groups),
        "duplicate_documents_beyond_first": duplicate_documents,
        "duplicate_pairs": duplicate_pairs,
        "groups_spanning_categories": cross_category_groups,
        "cross_category_duplicate_pairs": cross_category_pairs,
    }


def profile_version(version: str, documents: list[Document]) -> dict:
    char_lengths = [len(document.text) for document in documents]
    word_lengths = [len(document.text.split()) for document in documents]
    split_counts = Counter(document.split for document in documents)
    category_counts = Counter(document.category for document in documents)
    nonempty_chars = [length for length in char_lengths if length > 0]
    nonempty_words = [length for length in word_lengths if length > 0]

    return {
        "version": version,
        "source_url": DATASETS[version]["url"],
        "documents": len(documents),
        "categories": len(category_counts),
        "documents_by_split": dict(sorted(split_counts.items())),
        "documents_by_category": dict(sorted(category_counts.items())),
        "empty_or_whitespace_documents": sum(not document.text.strip() for document in documents),
        "characters": {
            "min": min(char_lengths, default=0),
            "median": statistics.median(char_lengths) if char_lengths else 0,
            "mean": round(statistics.fmean(char_lengths), 2) if char_lengths else 0,
            "p95": percentile(char_lengths, 0.95),
            "max": max(char_lengths, default=0),
        },
        "whitespace_tokens": {
            "min_nonempty": min(nonempty_words, default=0),
            "median": statistics.median(word_lengths) if word_lengths else 0,
            "mean": round(statistics.fmean(word_lengths), 2) if word_lengths else 0,
            "p95": percentile(word_lengths, 0.95),
            "max": max(word_lengths, default=0),
            "empty_documents": len(documents) - len(nonempty_words),
        },
        "exact_raw_text_duplicates": duplicate_metrics(documents, lambda text: text),
        "normalized_full_text_duplicates": duplicate_metrics(documents, normalize_text),
        "normalized_body_duplicates": duplicate_metrics(
            documents, lambda text: normalize_text(extract_body(text))
        ),
    }


def print_report(report: dict) -> None:
    print(f"\n=== {report['version']} ===")
    print(f"Documentos: {report['documents']:,}; categorías: {report['categories']}")
    print(f"Particiones: {report['documents_by_split']}")
    print(f"Documentos vacíos/blancos: {report['empty_or_whitespace_documents']:,}")
    chars = report["characters"]
    words = report["whitespace_tokens"]
    print(
        "Longitud en caracteres: "
        f"mediana={chars['median']}, media={chars['mean']}, p95={chars['p95']}, máximo={chars['max']}"
    )
    print(
        "Tokens separados por espacios: "
        f"mediana={words['median']}, media={words['mean']}, p95={words['p95']}, máximo={words['max']}"
    )
    for label, key in (
        ("Texto completo exacto", "exact_raw_text_duplicates"),
        ("Texto completo normalizado", "normalized_full_text_duplicates"),
        ("Cuerpo normalizado (cabeceras iniciales retiradas)", "normalized_body_duplicates"),
    ):
        duplicates = report[key]
        print(
            f"{label}: {duplicates['duplicate_groups']} grupos, "
            f"{duplicates['duplicate_documents_beyond_first']} copias extra, "
            f"{duplicates['duplicate_pairs']} pares; "
            f"{duplicates['groups_spanning_categories']} grupos en varias categorías"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="directorio de caché de los archivos originales",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "profiles" / "20news_profile.json",
        help="ruta del perfil JSON generado",
    )
    args = parser.parse_args()

    reports = []
    for version in DATASETS:
        report = profile_version(version, load_20newsgroups(args.data_dir, version))
        reports.append(report)
        print_report(report)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(reports, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nPerfil guardado en: {args.output}")


if __name__ == "__main__":
    main()
