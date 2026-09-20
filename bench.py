"""Run the shared five-query benchmark using R3's heading chunks.

R2 owns the shared questions in data/seller-warranty-policy/benchmark.json.
Each question supplies a gold answer, expected document, evidence terms, and
an optional audience filter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.agent import KnowledgeBaseAgent
from src.embeddings import GeminiEmbedder, LocalEmbedder, OpenAIEmbedder, _mock_embed
from src.heading_chunking import chunk_policy
from src.store import EmbeddingStore


CORPUS = Path("data/seller-warranty-policy")
CHUNKER = chunk_policy  # R3 strategy; other members change only this selection.
FILTER_TAG = re.compile(r"`?metadata_filter\s*=\s*(\{[^}]+\})`?")


class CachedEmbedder:
    """Persist embeddings by provider/model and exact text hash."""

    def __init__(self, embedder, cache_path: Path) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder
        self.name = getattr(embedder, "model_name", type(embedder).__name__)
        self.connection = sqlite3.connect(cache_path)
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, vector TEXT NOT NULL)"
        )

    def __call__(self, content: str) -> list[float]:
        key = hashlib.sha256((self.name + "\0" + content).encode("utf-8")).hexdigest()
        row = self.connection.execute("SELECT vector FROM embeddings WHERE key = ?", (key,)).fetchone()
        if row:
            return json.loads(row[0])
        vector = self.embedder(content)
        self.connection.execute(
            "INSERT INTO embeddings (key, vector) VALUES (?, ?)",
            (key, json.dumps(vector)),
        )
        self.connection.commit()
        return vector

    def prefetch(self, contents: list[str]) -> None:
        """Batch missing OpenAI embeddings; other providers use their normal calls."""
        if not isinstance(self.embedder, OpenAIEmbedder):
            for content in contents:
                self(content)
            return
        missing: dict[str, str] = {}
        for content in contents:
            key = hashlib.sha256((self.name + "\0" + content).encode("utf-8")).hexdigest()
            if self.connection.execute("SELECT 1 FROM embeddings WHERE key = ?", (key,)).fetchone() is None:
                missing[key] = content
        entries = list(missing.items())
        for start in range(0, len(entries), 64):
            batch = entries[start:start + 64]
            response = self.embedder.client.embeddings.create(
                model=self.name, input=[content for _, content in batch]
            )
            vectors = {item.index: item.embedding for item in response.data}
            if len(vectors) != len(batch):
                raise RuntimeError("Embedding API returned an incomplete batch")
            self.connection.executemany(
                "INSERT OR REPLACE INTO embeddings (key, vector) VALUES (?, ?)",
                [(key, json.dumps(vectors[index])) for index, (key, _) in enumerate(batch)],
            )
            self.connection.commit()

    def close(self) -> None:
        self.connection.close()


class FilteredStoreView:
    """Apply a query's audience filter when KnowledgeBaseAgent retrieves."""

    def __init__(self, store: EmbeddingStore, metadata_filter: dict | None) -> None:
        self.store = store
        self.metadata_filter = metadata_filter

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        return self.store.search_with_filter(query, top_k=top_k,
                                             metadata_filter=self.metadata_filter)


def load_queries(path: Path) -> list[dict]:
    if not path.exists():
        raise ValueError(f"Chưa có bộ câu hỏi chung của R2: {path}")
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        queries = data["queries"] if isinstance(data, dict) else data
    else:
        report = path.read_text(encoding="utf-8-sig")
        section = report.split("## 3. Câu hỏi đánh giá", 1)[-1]
        section = section.split("### Tổng hợp chất lượng", 1)[0]
        queries = []
        for line in section.splitlines():
            match = re.match(r"^\|\s*([1-5])\s*\|(.+)\|\s*$", line)
            if not match:
                continue
            cells = [cell.strip() for cell in match.group(2).split("|")]
            if len(cells) < 3 or not cells[0] or not cells[1]:
                continue
            question = cells[0]
            filter_match = FILTER_TAG.search(question)
            metadata_filter = json.loads(filter_match.group(1)) if filter_match else None
            if filter_match:
                question = FILTER_TAG.sub("", question).strip()
            queries.append({
                "query": question,
                "gold_answer": cells[1],
                "metadata_filter": metadata_filter,
            })

    if len(queries) != 5:
        raise ValueError(f"Cần đúng 5 câu hỏi từ R2; hiện đọc được {len(queries)} ở {path}")
    normalized = []
    for index, item in enumerate(queries, start=1):
        question = item.get("query") or item.get("question")
        gold = item.get("gold_answer") or item.get("gold")
        metadata_filter = item.get("metadata_filter") or None
        if not isinstance(question, str) or not question.strip() or not isinstance(gold, str) or not gold.strip():
            raise ValueError(f"Câu {index} thiếu query hoặc gold_answer")
        if metadata_filter is not None and not isinstance(metadata_filter, dict):
            raise ValueError(f"Câu {index} có metadata_filter không hợp lệ")
        terms = item.get("retrieval_terms") or []
        if not isinstance(terms, list) or not all(isinstance(term, str) for term in terms):
            raise ValueError(f"Câu {index} có retrieval_terms không hợp lệ")
        normalized.append({"query": question.strip(), "gold_answer": gold.strip(),
                           "metadata_filter": metadata_filter,
                           "gold_doc_id": item.get("gold_doc_id") or item.get("expected_doc_id"),
                           "answer_phrases": terms or ([item["answer_phrase"]] if item.get("answer_phrase") else [])})
    if not any(item["metadata_filter"] and "audience" in item["metadata_filter"] for item in normalized):
        raise ValueError("Bộ câu hỏi cần ít nhất một metadata_filter theo audience")
    return normalized


def load_evidence(path: Path) -> dict:
    """Optional R3-only evidence map: question number -> doc_id and answer phrase."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Evidence must be an object: {path}")
    return data


def _normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def assess(results: list[dict], gold_doc_id: str | None, answer_phrases: list[str]) -> dict | None:
    """Content-level retrieval proxy; final rubric still needs agent answer review."""
    if not gold_doc_id or not answer_phrases:
        return None
    needles = [_normalized(phrase) for phrase in answer_phrases]
    gold_results = [result for result in results
                    if result["metadata"].get("doc_id") == gold_doc_id]
    gold_context = _normalized(" ".join(result["content"] for result in gold_results))
    matched_terms = sum(needle in gold_context for needle in needles)
    document_rank = next((rank for rank, result in enumerate(results, start=1)
                          if result["metadata"].get("doc_id") == gold_doc_id), None)
    evidence_rank = next((rank for rank, result in enumerate(results, start=1)
                          if result["metadata"].get("doc_id") == gold_doc_id
                          and any(needle in _normalized(result["content"])
                                  for needle in needles)), None)
    complete = matched_terms == len(needles)
    return {
        "document_rank": document_rank,
        "evidence_rank": evidence_rank,
        "matched_terms": matched_terms,
        "required_terms": len(needles),
        "retrieval_score": 2 if complete and evidence_rank == 1 else 1 if complete and evidence_rank else 0,
    }


def make_embedder(provider: str):
    if provider == "mock":
        return _mock_embed
    load_dotenv(override=False)
    providers = {"local": LocalEmbedder, "openai": OpenAIEmbedder, "gemini": GeminiEmbedder}
    return CachedEmbedder(providers[provider](), CORPUS / "chunks" / "embedding-cache.sqlite3")


def make_llm(provider: str, model: str):
    if provider == "none":
        return None
    load_dotenv(override=False)
    from openai import OpenAI

    client = OpenAI()

    def answer(prompt: str) -> str:
        response = client.responses.create(model=model, input=prompt, store=False)
        return response.output_text.strip()

    return answer


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, default=CORPUS / "benchmark.json")
    parser.add_argument("--evidence", type=Path, default=Path("report/r3_evidence.json"))
    parser.add_argument("--output", type=Path, default=Path("report/ket_qua_benchmark_R3.txt"))
    parser.add_argument("--embedding", choices=["mock", "local", "openai", "gemini"], default="openai")
    parser.add_argument("--llm", choices=["none", "openai"], default="openai")
    parser.add_argument("--llm-model", default="gpt-4o-mini")
    args = parser.parse_args()
    try:
        queries = load_queries(args.queries)
        evidence = load_evidence(args.evidence)
    except (ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    embedder = make_embedder(args.embedding)
    llm_fn = make_llm(args.llm, args.llm_model)
    lines: list[str] = []

    def log(message: str = "") -> None:
        print(message)
        lines.append(message)

    try:
        chunks = [chunk for path in sorted(CORPUS.glob("*.md")) for chunk in CHUNKER(path, max_chars=1200)]
        if isinstance(embedder, CachedEmbedder):
            embedder.prefetch([chunk.content for chunk in chunks] + [item["query"] for item in queries])
        store = EmbeddingStore(collection_name="heading_benchmark", embedding_fn=embedder)
        store.add_documents(chunks)
        llm_name = args.llm_model if args.llm == "openai" else "none"
        log(f"Strategy: heading | Embedding: {args.embedding} | LLM: {llm_name} | "
            f"Chunks loaded: {store.get_collection_size()}")
        if args.embedding == "mock":
            log("Lưu ý: mock embedding không đo chất lượng truy xuất theo ngữ nghĩa.")
        for index, item in enumerate(queries, start=1):
            results = store.search_with_filter(item["query"], top_k=3,
                                               metadata_filter=item["metadata_filter"])
            log(f"\nQ{index}: {item['query']}")
            log(f"Filter: {item['metadata_filter']} | Gold: {item['gold_answer']}")
            for rank, result in enumerate(results, start=1):
                metadata = result["metadata"]
                log(f"  {rank}. score={result['score']:.4f} doc_id={metadata['doc_id']} "
                    f"chunk={result['id']} heading={metadata['heading_path']}")
                log(f"     {result['content'].replace(chr(10), ' ')[:180]}")
            if not results:
                log("  Không có chunk khớp bộ lọc.")
            detail = evidence.get(str(index), {})
            gold_doc_id = detail.get("gold_doc_id") or item["gold_doc_id"]
            answer_phrases = detail.get("answer_phrases") or item["answer_phrases"]
            if detail.get("answer_phrase"):
                answer_phrases = [detail["answer_phrase"]]
            assessment = assess(results, gold_doc_id, answer_phrases)
            if assessment is None:
                log("  Chưa chấm nội dung: cần expected_doc_id và retrieval_terms từ nguồn.")
            else:
                log(f"  document_rank={assessment['document_rank']} "
                    f"evidence_rank={assessment['evidence_rank']} "
                    f"terms={assessment['matched_terms']}/{assessment['required_terms']} "
                    f"retrieval_score={assessment['retrieval_score']}/2 "
                    "(cần kiểm câu trả lời agent để chấm rubric cuối)")
            if llm_fn is None:
                log("  Agent answer: chưa gọi LLM; dùng --llm openai để chấm câu trả lời.")
            else:
                agent = KnowledgeBaseAgent(FilteredStoreView(store, item["metadata_filter"]), llm_fn)
                log("  Agent answer: " + agent.answer(item["query"], top_k=3).replace("\n", " "))
                log("  Agent answer review: cần đối chiếu thủ công với gold answer và citation.")
            if item["metadata_filter"]:
                unfiltered = store.search_with_filter(item["query"], top_k=3, metadata_filter=None)
                log("  A/B không filter: " + ", ".join(
                    f"{result['id']} ({result['score']:.4f})" for result in unfiltered))
                log("  A/B có filter: " + ", ".join(
                    f"{result['id']} ({result['score']:.4f})" for result in results))
                if [r["id"] for r in unfiltered] == [r["id"] for r in results]:
                    log("  Hai top-3 giống nhau; câu này chưa chứng minh được lợi ích của filter.")
    finally:
        if isinstance(embedder, CachedEmbedder):
            embedder.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved results: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
