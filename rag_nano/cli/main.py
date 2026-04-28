from __future__ import annotations

import shutil
from pathlib import Path

import typer
import uvicorn

from rag_nano.api.app import create_app
from rag_nano.components.embedding import get_embedding_provider
from rag_nano.components.structured_store import get_structured_store
from rag_nano.components.vector_store import get_vector_store
from rag_nano.config import Settings
from rag_nano.core.ingest import ingest as _ingest_core
from rag_nano.types import DataType

app = typer.Typer(help="rag-nano — minimum closed-loop librarian")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8089, "--port"),
) -> None:
    settings = Settings.from_env()
    uvicorn.run(create_app(settings), host=host, port=port)


@app.command()
def ingest(
    paths: list[Path] = typer.Argument(..., exists=True),
    data_type: DataType | None = typer.Option(None, "--data-type", "-t"),
    category: str | None = typer.Option(None, "--category", "-c"),
) -> None:
    settings = Settings.from_env()
    structured = get_structured_store(settings)
    vector = get_vector_store(settings)

    # Expand directories to individual files
    expanded: list[Path] = []
    for p in paths:
        if p.is_dir():
            expanded.extend(f for f in p.iterdir() if f.is_file())
        else:
            expanded.append(p)

    report = _ingest_core(
        expanded,
        structured,
        vector,
        settings,
    )

    typer.echo("\nIngest Report")
    typer.echo(f"  accepted: {report.accepted}")
    typer.echo(f"  rejected: {report.rejected}")
    typer.echo(f"  total chunks: {report.total_chunks}")
    if report.by_data_type:
        typer.echo("  by data_type:")
        for dtype, count in report.by_data_type.items():
            typer.echo(f"    {dtype}: {count}")
    if report.per_item_reasons:
        typer.echo("\n  per-item:")
        for path, reason in report.per_item_reasons:
            if reason:
                typer.echo(f"    ✗ {path} → {reason}")
            else:
                typer.echo(f"    ✓ {path}")


@app.command()
def wipe_index(
    yes: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    if not yes:
        typer.confirm("This will delete ALL indexed data. Continue?", abort=True)
    settings = Settings.from_env()
    index_dir = settings.index_dir
    if index_dir.exists():
        shutil.rmtree(index_dir)
    typer.echo("Index wiped.")


@app.command()
def stats() -> None:
    settings = Settings.from_env()
    structured = get_structured_store(settings)
    s = structured.get_stats()
    typer.echo(f"Chunk count:  {s['chunk_count']}")
    typer.echo(f"Source count: {s['source_count']}")
    if s["by_data_type"]:
        typer.echo("By data_type:")
        for dtype, count in s["by_data_type"].items():
            typer.echo(f"  {dtype}: {count}")
    if s["last_ingest_at"]:
        typer.echo(f"Last ingest: {s['last_ingest_at']}")


if __name__ == "__main__":
    app()
