from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer
import uvicorn

from rag_nano.api.app import create_app
from rag_nano.components.embedding import get_embedding_provider
from rag_nano.components.reranker import get_reranker
from rag_nano.components.retriever import get_retriever
from rag_nano.components.structured_store import get_structured_store
from rag_nano.components.vector_store import get_vector_store
from rag_nano.config import Settings
from rag_nano.core.ingest import ingest as _ingest_core
from rag_nano.core.retrieval import Components
from rag_nano.eval.runner import run_eval
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


@app.command()
def eval(
    cases: Path = typer.Option(
        Path("eval/cases.yaml"), "--cases", help="Path to cases.yaml"
    ),
    history: Path = typer.Option(
        Path("eval/history.jsonl"), "--history", help="Path to history.jsonl"
    ),
    k: int = typer.Option(5, "--k"),
    out: str = typer.Option("-", "--out", help="Path to write JSON record; '-' = stdout"),
    fail_on_regression: bool = typer.Option(False, "--fail-on-regression"),
) -> None:
    settings = Settings.from_env()
    components = Components(
        embedding_provider=get_embedding_provider(settings),
        vector_store=get_vector_store(settings),
        retriever=get_retriever(settings),
        reranker=get_reranker(settings),
        structured_store=get_structured_store(settings),
    )
    run = run_eval(cases, history, components, settings, k=k)

    typer.echo(f"recall@{run.k} = {run.metric_recall_at_k:.4f}")
    typer.echo(f"hit_rate    = {run.metric_hit_rate:.4f}")
    typer.echo(f"cases       = {run.case_count}")
    if run.delta_vs_previous is not None:
        typer.echo(
            f"delta vs previous: recall {run.delta_vs_previous['recall_delta']:+.4f}, "
            f"hit_rate {run.delta_vs_previous['hit_rate_delta']:+.4f}"
        )
    else:
        typer.echo("delta vs previous: (first run)")

    record = {
        "run_id": run.run_id,
        "metric_recall_at_k": run.metric_recall_at_k,
        "metric_hit_rate": run.metric_hit_rate,
        "case_count": run.case_count,
        "k": run.k,
        "delta_vs_previous": run.delta_vs_previous,
    }
    record_json = json.dumps(record, ensure_ascii=False)
    if out == "-":
        typer.echo(record_json)
    else:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(record_json + "\n", encoding="utf-8")

    if fail_on_regression and run.delta_vs_previous is not None:
        if run.delta_vs_previous["recall_delta"] < 0:
            raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
