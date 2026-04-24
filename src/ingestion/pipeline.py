"""Ingestion pipeline orchestration for the C-stage MVP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol

from core.settings import Settings
from core.trace import TraceCollector, TraceContext
from core.types import Chunk, Document
from ingestion.chunking.document_chunker import DocumentChunker
from ingestion.embedding.batch_processor import BatchProcessor
from ingestion.embedding.dense_encoder import DenseEncoder
from ingestion.embedding.sparse_encoder import SparseEncoder
from ingestion.storage.bm25_indexer import BM25Indexer
from ingestion.storage.image_storage import ImageStorage
from ingestion.storage.vector_upserter import VectorUpserter
from ingestion.transform.chunk_refiner import ChunkRefiner
from ingestion.transform.image_captioner import ImageCaptioner
from ingestion.transform.metadata_enricher import MetadataEnricher
from libs.loader.file_integrity import SQLiteIntegrityChecker
from libs.loader.pdf_loader import PdfLoader


class LoaderProtocol(Protocol):
    def load(self, path: str) -> Document: ...


class IntegrityCheckerProtocol(Protocol):
    def compute_sha256(self, path: str) -> str: ...
    def should_skip(self, file_hash: str) -> bool: ...
    def mark_success(self, file_hash: str, file_path: str) -> None: ...
    def mark_failed(self, file_hash: str, error_msg: str) -> None: ...


@dataclass(slots=True)
class PipelineResult:
    """Result summary for a single ingestion run."""

    file_hash: str
    document_id: str | None
    chunk_count: int
    dense_vector_count: int
    sparse_vector_count: int
    vector_ids: list[str]
    stored_image_paths: list[str]
    skipped: bool = False


class PipelineError(RuntimeError):
    """Raised when a pipeline stage fails."""


class IngestionPipeline:
    """Run integrity, load, split, transform, encode, and store stages in order."""

    def __init__(
        self,
        settings: Settings,
        integrity_checker: IntegrityCheckerProtocol | None = None,
        loader: LoaderProtocol | None = None,
        chunker: DocumentChunker | None = None,
        transforms: list[object] | None = None,
        batch_processor: BatchProcessor | None = None,
        bm25_indexer: BM25Indexer | None = None,
        vector_upserter: VectorUpserter | None = None,
        image_storage: ImageStorage | None = None,
    ) -> None:
        self._settings = settings
        self._integrity_checker = integrity_checker or SQLiteIntegrityChecker()
        self._loader = loader or PdfLoader(settings)
        self._chunker = chunker or DocumentChunker(settings)
        self._transforms = transforms or [
            ChunkRefiner(settings),
            MetadataEnricher(settings),
            ImageCaptioner(settings),
        ]
        self._batch_processor = batch_processor or BatchProcessor(
            dense_encoder=DenseEncoder(settings),
            sparse_encoder=SparseEncoder(),
            batch_size=2,
        )
        self._bm25_indexer = bm25_indexer or BM25Indexer()
        self._vector_upserter = vector_upserter or VectorUpserter(settings)
        self._image_storage = image_storage or ImageStorage()

    def run(
        self,
        path: str,
        collection: str,
        force: bool = False,
        trace: TraceContext | None = None,
        on_progress=None,
    ) -> PipelineResult:
        """Run the end-to-end ingestion pipeline for a single document."""

        owned_trace = trace is None
        trace = trace or TraceContext(trace_type="ingestion")
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        file_hash = self._integrity_checker.compute_sha256(str(file_path))
        if not force and self._integrity_checker.should_skip(file_hash):
            if owned_trace:
                trace.finish()
                TraceCollector().collect(trace)
            return PipelineResult(
                file_hash=file_hash,
                document_id=None,
                chunk_count=0,
                dense_vector_count=0,
                sparse_vector_count=0,
                vector_ids=[],
                stored_image_paths=[],
                skipped=True,
            )

        try:
            integrity_started = perf_counter()
            trace.record_stage(
                "integrity",
                {
                    "file_hash": file_hash,
                    "force": force,
                    "method": "sha256",
                    "elapsed_ms": round((perf_counter() - integrity_started) * 1000, 3),
                },
            )
            _report_progress(on_progress, "integrity", 1, 6)

            load_started = perf_counter()
            document = self._loader.load(str(file_path))
            trace.record_stage(
                "load",
                {
                    "document_id": document.id,
                    "method": type(self._loader).__name__.replace("Loader", "").lower() or "loader",
                    "elapsed_ms": round((perf_counter() - load_started) * 1000, 3),
                },
            )
            _report_progress(on_progress, "load", 2, 6)

            stored_image_paths = self._persist_document_images(document, collection)

            split_started = perf_counter()
            chunks = self._chunker.split_document(document)
            chunks = self._attach_collection(chunks, collection)
            trace.record_stage(
                "split",
                {
                    "chunk_count": len(chunks),
                    "method": self._settings.splitter.provider,
                    "elapsed_ms": round((perf_counter() - split_started) * 1000, 3),
                },
            )
            _report_progress(on_progress, "split", 3, 6)

            transform_started = perf_counter()
            for transform in self._transforms:
                chunks = transform.transform(chunks, trace=trace)
            trace.record_stage(
                "transform",
                {
                    "chunk_count": len(chunks),
                    "method": "pipeline_transforms",
                    "transform_count": len(self._transforms),
                    "elapsed_ms": round((perf_counter() - transform_started) * 1000, 3),
                },
            )
            _report_progress(on_progress, "transform", 4, 6)

            embed_started = perf_counter()
            batch_result = self._batch_processor.process(chunks, trace=trace)
            trace.record_stage(
                "embed",
                {
                    "chunk_count": len(chunks),
                    "method": self._settings.embedding.provider,
                    "dense_count": len(batch_result.dense_vectors),
                    "sparse_count": len(batch_result.sparse_vectors),
                    "elapsed_ms": round((perf_counter() - embed_started) * 1000, 3),
                },
            )
            _report_progress(on_progress, "embed", 5, 6)

            upsert_started = perf_counter()
            vector_ids = self._vector_upserter.upsert(
                chunks,
                batch_result.dense_vectors,
                trace=trace,
            )
            self._bm25_indexer.build(
                chunks,
                batch_result.sparse_vectors,
                trace=trace,
                incremental=True,
            )
            trace.record_stage(
                "upsert",
                {
                    "vector_count": len(vector_ids),
                    "image_count": len(stored_image_paths),
                    "method": self._settings.vector_store.provider,
                    "elapsed_ms": round((perf_counter() - upsert_started) * 1000, 3),
                },
            )
            _report_progress(on_progress, "upsert", 6, 6)

            self._integrity_checker.mark_success(file_hash, str(file_path))
            if owned_trace:
                trace.finish()
                TraceCollector().collect(trace)
            return PipelineResult(
                file_hash=file_hash,
                document_id=document.id,
                chunk_count=len(chunks),
                dense_vector_count=len(batch_result.dense_vectors),
                sparse_vector_count=len(batch_result.sparse_vectors),
                vector_ids=vector_ids,
                stored_image_paths=stored_image_paths,
                skipped=False,
            )
        except Exception as error:
            self._integrity_checker.mark_failed(file_hash, str(error))
            if owned_trace:
                trace.finish()
                TraceCollector().collect(trace)
            raise PipelineError(f"Pipeline failed at {file_path.name}: {error}") from error

    def _attach_collection(self, chunks: list[Chunk], collection: str) -> list[Chunk]:
        updated_chunks: list[Chunk] = []
        for chunk in chunks:
            metadata = dict(chunk.metadata)
            metadata["collection"] = collection
            updated_chunks.append(
                Chunk(
                    id=chunk.id,
                    text=chunk.text,
                    metadata=metadata,
                    start_offset=chunk.start_offset,
                    end_offset=chunk.end_offset,
                    source_ref=chunk.source_ref,
                )
            )
        return updated_chunks

    def _persist_document_images(self, document: Document, collection: str) -> list[str]:
        images = document.metadata.get("images")
        if not isinstance(images, list):
            return []

        stored_paths: list[str] = []
        for image in images:
            if not isinstance(image, dict):
                continue
            image_id = image.get("id")
            image_path = image.get("path")
            if not isinstance(image_id, str) or not isinstance(image_path, str):
                continue

            candidate = Path(image_path)
            if not candidate.exists():
                continue

            stored_path = self._image_storage.save_image(
                image_id=image_id,
                image_bytes=candidate.read_bytes(),
                collection=collection,
                doc_hash=document.id,
                page_num=image.get("page") if isinstance(image.get("page"), int) else None,
                extension=candidate.suffix or ".png",
            )
            image["path"] = stored_path
            stored_paths.append(stored_path)

        return stored_paths


def _report_progress(on_progress, stage_name: str, current: int, total: int) -> None:
    if on_progress is None:
        return
    on_progress(stage_name, current, total)
