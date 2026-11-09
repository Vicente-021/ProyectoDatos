"""Measure token and distinct-shingle counts for both 20 Newsgroups versions."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

if __package__:
    from .loader import DATASETS, Document, load_20newsgroups
    from .preprocessing import preprocess_to_tokens
    from .shingling import word_shingles
else:  # allows: python3 src/profile_shingling.py
    from loader import DATASETS, Document, load_20newsgroups
    from preprocessing import preprocess_to_tokens
    from shingling import word_shingles


K = 5


def _percentile(values: list[int], q: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(q * len(ordered) + 0.999999) - 1))
    return ordered[index]


def profile_documents(documents: list[Document], version: str, k: int = K) -> dict:
    token_counts: list[int] = []
    shingle_counts: list[int] = []
    counts_by_category: dict[str, list[tuple[int, int]]] = defaultdict(list)

    for document in documents:
        tokens = preprocess_to_tokens(document.text)
        shingles = word_shingles(tokens, k=k)
        token_count = len(tokens)
        shingle_count = len(shingles)
        token_counts.append(token_count)
        shingle_counts.append(shingle_count)
        counts_by_category[document.category].append((token_count, shingle_count))

    def distribution(values: list[int]) -> dict:
        return {
            "min": min(values, default=0),
            "median": statistics.median(values) if values else 0,
            "mean": round(statistics.fmean(values), 2) if values else 0,
            "p95": _percentile(values, 0.95),
            "max": max(values, default=0),
            "zero_count": sum(value == 0 for value in values),
        }

    return {
        "version": version,
        "source_url": DATASETS[version]["url"],
        "k_words": k,
        "tokenizer": "Unicode alphanumeric runs; numbers retained; punctuation and underscores delimit tokens",
        "normalization": (
            "NFKC, casefold, collapse whitespace, remove recognizable initial email/news headers "
            "and signature after a standalone -- line; preserve quoted text; no stemming or stop-word removal"
        ),
        "documents": len(documents),
        "categories": len(counts_by_category),
        "total_tokens": sum(token_counts),
        "total_distinct_shingles_across_documents": sum(shingle_counts),
        "documents_shorter_than_k": sum(count < k for count in token_counts),
        "tokens_per_document": distribution(token_counts),
        "distinct_shingles_per_document": distribution(shingle_counts),
        "by_category": {
            category: {
                "documents": len(values),
                "mean_tokens": round(statistics.fmean(t for t, _ in values), 2),
                "mean_distinct_shingles": round(statistics.fmean(s for _, s in values), 2),
            }
            for category, values in sorted(counts_by_category.items())
        },
    }


def print_profile(profile: dict) -> None:
    token_stats = profile["tokens_per_document"]
    shingle_stats = profile["distinct_shingles_per_document"]
    print(f"\n=== {profile['version']}: shingles de {profile['k_words']} palabras ===")
    print(f"Documentos: {profile['documents']:,}; categorías: {profile['categories']}")
    print(f"Total tokens: {profile['total_tokens']:,}")
    print(f"Suma de shingles distintos por documento: {profile['total_distinct_shingles_across_documents']:,}")
    print(f"Docs con menos de k tokens: {profile['documents_shorter_than_k']:,}")
    print(
        "Tokens/documento: "
        f"mediana={token_stats['median']}, media={token_stats['mean']}, p95={token_stats['p95']}"
    )
    print(
        "Shingles/documento: "
        f"mediana={shingle_stats['median']}, media={shingle_stats['mean']}, p95={shingle_stats['p95']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="directorio donde están los archivos originales",
    )
    parser.add_argument("--k", type=int, default=K, help="tamaño del shingle en palabras")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "profiles" / "shingle_profile_k5.json",
        help="ruta del perfil JSON generado",
    )
    args = parser.parse_args()
    if args.k < 1:
        parser.error("--k debe ser al menos 1")

    profiles = []
    for version in DATASETS:
        documents = load_20newsgroups(args.data_dir, version)
        profile = profile_documents(documents, version, k=args.k)
        print_profile(profile)
        profiles.append(profile)
        del documents

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(profiles, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nPerfil guardado en: {args.output}")


if __name__ == "__main__":
    main()
