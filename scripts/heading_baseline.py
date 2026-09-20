"""Reproducible structural baseline for seller warranty policy chunking.

Run from the repository root: py -3.11 -m scripts.heading_baseline
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.chunking import ChunkingStrategyComparator
from src.heading_chunking import chunk_policy, read_policy


CORPUS = Path("data/seller-warranty-policy")
CHUNK_SIZE = 1200
BASELINE_DOCS = {
    "tiktok-dieu-khoan-bao-hanh-bat-cong",
    "tiktok-huong-dan-dang-ban-bao-hanh",
    "tiktok-quy-che-bao-hanh",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--save-chunks",
        nargs="?",
        const="data/seller-warranty-policy/chunks/heading-1200.jsonl",
        metavar="PATH",
        help="write one chunk per JSONL line (default path when no PATH follows)",
    )
    args = parser.parse_args()
    paths = sorted(CORPUS.glob("*.md"))
    if len(paths) != 5:
        raise RuntimeError(f"Expected 5 policies, found {len(paths)}")
    comparator = ChunkingStrategyComparator()
    print(f"Corpus: {CORPUS} | max_chars={CHUNK_SIZE}")
    print("\nAll documents, heading strategy:")
    print("doc_id | body_chars | chunks | avg_chars | max_chars | oversized_sections")
    print("--- | ---: | ---: | ---: | ---: | ---:")
    for path in paths:
        metadata, body = read_policy(path)
        chunks = chunk_policy(path, CHUNK_SIZE)
        lengths = [len(c.content) for c in chunks]
        oversized = len({c.metadata["heading_path"] for c in chunks
                         if c.metadata["split_method"] == "heading+recursive"})
        print(f"{metadata['doc_id']} | {len(body)} | {len(chunks)} | "
              f"{sum(lengths) / len(lengths):.1f} | {max(lengths)} | {oversized}")

    print("\nThree-document structural baseline:")
    print("doc_id | strategy | chunks | avg_chars | max_chars")
    print("--- | --- | ---: | ---: | ---:")
    for path in paths:
        metadata, body = read_policy(path)
        if metadata["doc_id"] not in BASELINE_DOCS:
            continue
        results = comparator.compare(body, chunk_size=CHUNK_SIZE)
        heading = chunk_policy(path, CHUNK_SIZE)
        results["by_heading"] = {
            "count": len(heading),
            "avg_length": sum(len(c.content) for c in heading) / len(heading),
            "chunks": [c.content for c in heading],
        }
        for name, stats in results.items():
            print(f"{metadata['doc_id']} | {name} | {stats['count']} | "
                  f"{stats['avg_length']:.1f} | "
                  f"{max(map(len, stats['chunks']), default=0)}")

    if args.save_chunks:
        destination = Path(args.save_chunks)
        destination.parent.mkdir(parents=True, exist_ok=True)
        chunks = [chunk for path in paths for chunk in chunk_policy(path, CHUNK_SIZE)]
        with destination.open("w", encoding="utf-8", newline="\n") as output:
            for chunk in chunks:
                output.write(json.dumps({
                    "id": chunk.id,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                }, ensure_ascii=False) + "\n")
        print(f"\nSaved {len(chunks)} chunks to {destination}")


if __name__ == "__main__":
    main()
