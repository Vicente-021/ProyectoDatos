"""Carga reproducible del corpus 20 Newsgroups, sin dependencias externas.

El archivo original se conserva en data/raw y se lee directamente desde el
tar.gz: no se extraen archivos individuales ni se modifican los mensajes.
"""

from __future__ import annotations

import argparse
import hashlib
import tarfile
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


DATASETS = {
    "bydate": {
        "url": "https://ndownloader.figshare.com/files/5975967",
        "archive_name": "20news-bydate.tar.gz",
        "sha256": "8f1b2514ca22a5ade8fbb9cfa5727df95fa587f4c87b786e15c759fa66d95610",
        "roots": {
            "20news-bydate-train": "train",
            "20news-bydate-test": "test",
        },
    },
    "original": {
        "url": "https://people.csail.mit.edu/jrennie/20Newsgroups/20news-19997.tar.gz",
        "archive_name": "20news-19997.tar.gz",
        # SHA-256 recorded from the official archive downloaded for this project.
        "sha256": "ab7bbf82b7831f7dbb1a09d9312f66fa78565c8de25526999b0d66f69d37e414",
        "roots": {"20_newsgroups": "all"},
    },
}


@dataclass(frozen=True)
class Document:
    """Un documento del corpus, conservado sin preprocesar."""

    doc_id: str
    split: str
    category: str
    text: str
    source_path: str


def download_archive(destination: Path, version: str = "bydate") -> Path:
    """Descarga o valida el archivo de una versión del corpus."""
    if version not in DATASETS:
        raise ValueError(f"Versión desconocida: {version}. Opciones: {', '.join(DATASETS)}")
    spec = DATASETS[version]
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and _is_valid_archive(destination, spec):
        return destination
    if destination.exists():
        destination.unlink()

    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(
        spec["url"],
        headers={"User-Agent": "20Newsgroups-course-project/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            with temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
        if not _is_valid_archive(temporary, spec):
            raise ValueError("La descarga no parece ser el archivo 20 Newsgroups esperado.")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return destination


def _is_valid_archive(path: Path, spec: dict) -> bool:
    """Comprueba SHA-256 y que el tar.gz contenga la estructura esperada."""
    try:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != spec["sha256"]:
            return False

        with tarfile.open(path, mode="r:gz") as archive:
            roots = {
                PurePosixPath(member.name).parts[0]
                for member in archive.getmembers()
                if member.isfile() and PurePosixPath(member.name).parts
            }
        return set(spec["roots"]).issubset(roots)
    except (OSError, tarfile.TarError, EOFError):
        return False


def load_documents(archive_path: Path, version: str = "bydate") -> list[Document]:
    """Lee documentos y etiquetas del archivo, sin limpiar ni transformar texto."""
    if version not in DATASETS:
        raise ValueError(f"Versión desconocida: {version}. Opciones: {', '.join(DATASETS)}")
    root_to_split = DATASETS[version]["roots"]
    records: list[Document] = []

    # El modo de streaming evita buscar repetidamente dentro del gzip, lo que
    # obligaría a descomprimir desde el inicio para cada mensaje.
    with tarfile.open(archive_path, mode="r|gz") as archive:
        for member in archive:
            if not member.isfile():
                continue

            parts = PurePosixPath(member.name).parts
            if len(parts) < 3 or parts[0] not in root_to_split:
                continue

            split = root_to_split[parts[0]]
            category = parts[1]
            stream = archive.extractfile(member)
            if stream is None:
                continue

            raw = stream.read()
            text = raw.decode("utf-8", errors="replace")
            relative_path = "/".join(parts[2:])
            doc_id = f"{split}/{category}/{relative_path}"
            records.append(
                Document(
                    doc_id=doc_id,
                    split=split,
                    category=category,
                    text=text,
                    source_path=member.name,
                )
            )

    if not records:
        raise ValueError(f"No se encontraron mensajes de 20 Newsgroups en {archive_path}.")
    return sorted(records, key=lambda document: document.doc_id)


def load_20newsgroups(data_dir: Path, version: str = "bydate") -> list[Document]:
    """Carga una versión del corpus desde caché local o la descarga."""
    if version not in DATASETS:
        raise ValueError(f"Versión desconocida: {version}. Opciones: {', '.join(DATASETS)}")
    archive_path = data_dir / "raw" / DATASETS[version]["archive_name"]
    download_archive(archive_path, version)
    return load_documents(archive_path, version)


def summarize(documents: Iterable[Document]) -> None:
    """Imprime un resumen reproducible sin revelar contenido de mensajes."""
    docs = list(documents)
    by_split = Counter(document.split for document in docs)
    by_category = Counter(document.category for document in docs)
    categories = sorted(by_category)

    print(f"Documentos cargados: {len(docs):,}")
    print(f"Categorías: {len(categories)}")
    print("Por partición:")
    for split in ("train", "test"):
        print(f"  {split}: {by_split[split]:,}")
    print("Categorías:")
    for category in categories:
        print(f"  {category}: {by_category[category]:,}")
    print("Texto conservado sin preprocesar; cada documento incluye id, categoría y partición.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="directorio donde se guardará el archivo original (default: ./data)",
    )
    parser.add_argument(
        "--version",
        choices=(*DATASETS, "both"),
        default="bydate",
        help="versión del corpus que se cargará",
    )
    args = parser.parse_args()

    versions = DATASETS if args.version == "both" else (args.version,)
    for version in versions:
        print(f"\n=== 20 Newsgroups: {version} ===")
        documents = load_20newsgroups(args.data_dir, version)
        summarize(documents)


if __name__ == "__main__":
    main()
